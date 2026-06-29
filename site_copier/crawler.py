"""The crawler that drives the copy: fetch -> save -> discover -> rewrite."""

import json
import os
import queue
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field

from . import extract
from .urls import (
    host_of,
    local_path_for,
    normalize_url,
    relative_link,
    split_fragment,
)

DEFAULT_UA = "site-copier/0.1 (+https://github.com/brucedsny/job-agent)"


@dataclass
class CrawlStats:
    pages: int = 0
    assets: int = 0
    failed: int = 0
    bytes: int = 0
    errors: list = field(default_factory=list)


class _Resource:
    __slots__ = ("url", "local_path", "content_type")

    def __init__(self, url, local_path, content_type):
        self.url = url
        self.local_path = local_path
        self.content_type = content_type


class SiteCopier:
    """Copy an entire website to a local directory for offline browsing."""

    def __init__(
        self,
        seed,
        outdir,
        *,
        max_pages=500,
        max_depth=10,
        cross_host_assets=True,
        allowed_hosts=None,
        delay=0.0,
        workers=4,
        timeout=30,
        user_agent=DEFAULT_UA,
        respect_robots=False,
        verbose=True,
        manifest_name="manifest.json",
    ):
        seed = normalize_url(seed) or normalize_url("http://" + seed)
        if not seed:
            raise ValueError("invalid seed URL")
        self.seed = seed
        self.seed_host = host_of(seed)
        self.outdir = os.path.abspath(outdir)
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.cross_host_assets = cross_host_assets
        self.allowed_hosts = set(allowed_hosts or [self.seed_host])
        self.delay = delay
        self.workers = max(1, workers)
        self.timeout = timeout
        self.user_agent = user_agent
        self.respect_robots = respect_robots
        self.verbose = verbose
        self.manifest_name = manifest_name

        self._q = queue.Queue()
        self._lock = threading.Lock()
        self._seen = set()
        self._page_count = 0
        self._downloaded = {}  # normalized url -> _Resource
        self.stats = CrawlStats()
        self._robots = self._load_robots() if respect_robots else None

    # -- public ------------------------------------------------------------
    def run(self):
        os.makedirs(self.outdir, exist_ok=True)
        self._enqueue(self.seed, "page", 0)

        threads = [
            threading.Thread(target=self._worker, daemon=True)
            for _ in range(self.workers)
        ]
        for t in threads:
            t.start()
        self._q.join()
        for _ in threads:
            self._q.put(None)
        for t in threads:
            t.join()

        self._rewrite_all()
        self._write_manifest()
        self._log(
            "done: %d pages, %d assets, %d failed (%s)"
            % (
                self.stats.pages,
                self.stats.assets,
                self.stats.failed,
                _human(self.stats.bytes),
            )
        )
        return self.stats

    # -- queue / scheduling ------------------------------------------------
    def _enqueue(self, url, kind, depth):
        norm = normalize_url(url)
        if norm is None or not self._allowed(norm, kind):
            return
        with self._lock:
            if norm in self._seen:
                return
            if kind == "page":
                if depth > self.max_depth or self._page_count >= self.max_pages:
                    return
                self._page_count += 1
            self._seen.add(norm)
        self._q.put((norm, kind, depth))

    def _allowed(self, url, kind):
        host = host_of(url)
        if kind == "page":
            if host not in self.allowed_hosts:
                return False
        else:  # asset
            if not self.cross_host_assets and host not in self.allowed_hosts:
                return False
        if self._robots is not None and not self._robots_ok(url):
            self._log("robots: skip %s" % url)
            return False
        return True

    def _worker(self):
        while True:
            item = self._q.get()
            if item is None:
                self._q.task_done()
                return
            url, kind, depth = item
            try:
                self._process(url, kind, depth)
            except Exception as exc:  # never let one URL kill the worker
                self.stats.failed += 1
                self.stats.errors.append("%s: %s" % (url, exc))
                self._log("error %s: %s" % (url, exc))
            finally:
                if self.delay:
                    time.sleep(self.delay)
                self._q.task_done()

    # -- fetch / save ------------------------------------------------------
    def _process(self, url, kind, depth):
        body, final_url, ctype = self._fetch(url)
        local = local_path_for(final_url)
        self._write_file(local, body)

        resource = _Resource(final_url, local, ctype)
        with self._lock:
            self._downloaded[url] = resource
            self._downloaded[normalize_url(final_url) or final_url] = resource
            self.stats.bytes += len(body)
            if kind == "page":
                self.stats.pages += 1
            else:
                self.stats.assets += 1

        self._log("saved [%s] %s -> %s" % (kind, final_url, local))

        if "html" in ctype:
            pages, assets = extract.extract_html(_decode(body, ctype), final_url)
            for u in pages:
                self._enqueue(u, "page", depth + 1)
            for u in assets:
                self._enqueue(u, "asset", depth)
        elif "css" in ctype:
            for u in extract.extract_css(_decode(body, ctype), final_url):
                self._enqueue(u, "asset", depth)

    def _fetch(self, url):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = resp.read()
            final_url = resp.geturl()
            ctype = resp.headers.get("Content-Type", "").lower()
        return body, final_url, ctype

    def _write_file(self, local, body):
        dest = os.path.join(self.outdir, local)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        # A URL may want to be both a file and a directory (rare). If a parent
        # path is already a file, fall back to a sibling name.
        try:
            with open(dest, "wb") as fh:
                fh.write(body)
        except (NotADirectoryError, IsADirectoryError, FileExistsError):
            pass

    # -- rewrite pass ------------------------------------------------------
    def _rewrite_all(self):
        seen_paths = set()
        for resource in self._downloaded.values():
            if resource.local_path in seen_paths:
                continue
            seen_paths.add(resource.local_path)
            ctype = resource.content_type
            if "html" not in ctype and "css" not in ctype:
                continue
            dest = os.path.join(self.outdir, resource.local_path)
            try:
                with open(dest, "rb") as fh:
                    raw = fh.read()
            except OSError:
                continue
            text = _decode(raw, ctype)
            mapper = self._make_mapper(resource.local_path)
            if "html" in ctype:
                text = extract.rewrite_html(text, resource.url, mapper)
            else:
                text = extract.rewrite_css(text, resource.url, mapper)
            with open(dest, "wb") as fh:
                fh.write(text.encode("utf-8", "replace"))

    def _make_mapper(self, source_local):
        downloaded = self._downloaded

        def mapper(absolute_url):
            base, frag = split_fragment(absolute_url)
            norm = normalize_url(base)
            if norm is None:
                return None
            resource = downloaded.get(norm)
            if resource is not None:
                return relative_link(source_local, resource.local_path) + frag
            # Not part of the copy: keep it as a live absolute URL.
            return base + frag

        return mapper

    # -- robots ------------------------------------------------------------
    def _load_robots(self):
        scheme = urllib.parse.urlsplit(self.seed).scheme or "http"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url("%s://%s/robots.txt" % (scheme, self.seed_host))
        try:
            rp.read()
        except Exception:
            return None
        return rp

    def _robots_ok(self, url):
        try:
            return self._robots.can_fetch(self.user_agent, url)
        except Exception:
            return True

    # -- misc --------------------------------------------------------------
    def _write_manifest(self):
        seen = set()
        entries = []
        for resource in self._downloaded.values():
            if resource.local_path in seen:
                continue
            seen.add(resource.local_path)
            entries.append(
                {
                    "url": resource.url,
                    "path": resource.local_path,
                    "content_type": resource.content_type,
                }
            )
        manifest = {
            "seed": self.seed,
            "pages": self.stats.pages,
            "assets": self.stats.assets,
            "failed": self.stats.failed,
            "bytes": self.stats.bytes,
            "resources": sorted(entries, key=lambda e: e["path"]),
            "errors": self.stats.errors,
        }
        with open(os.path.join(self.outdir, self.manifest_name), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)

    def _log(self, msg):
        if self.verbose:
            print(msg, flush=True)


def _decode(body, ctype):
    charset = "utf-8"
    if "charset=" in ctype:
        charset = ctype.split("charset=", 1)[1].split(";")[0].strip() or "utf-8"
    try:
        return body.decode(charset, "replace")
    except (LookupError, TypeError):
        return body.decode("utf-8", "replace")


def _human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return "%.1f %s" % (n, unit)
        n /= 1024.0

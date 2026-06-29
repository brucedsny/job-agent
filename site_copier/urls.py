"""URL helpers: normalization and mapping URLs to local file paths.

The mapping rules here are applied uniformly so that the file saver and the link
rewriter always agree on where a given URL lives on disk.
"""

import hashlib
import posixpath
import re
from urllib.parse import urljoin, urlsplit, urlunsplit, unquote

HTTP_SCHEMES = ("http", "https")

# Characters that are awkward/illegal in file names across common filesystems.
_ILLEGAL = re.compile(r'[<>:"\\|?*\x00-\x1f]')


def normalize_url(url, base=None):
    """Resolve ``url`` (optionally against ``base``), drop the fragment and
    normalize the path. Returns ``None`` for non-HTTP(S) URLs (mailto:, data:,
    javascript:, tel:, ...).
    """
    if base:
        url = urljoin(base, url)
    parts = urlsplit(url.strip())
    if parts.scheme not in HTTP_SCHEMES:
        return None
    netloc = parts.netloc.lower()
    if not netloc:
        return None

    raw_path = parts.path or "/"
    trailing = raw_path.endswith("/")
    path = posixpath.normpath(raw_path)
    if path == ".":
        path = "/"
    if trailing and not path.endswith("/"):
        path += "/"
    return urlunsplit((parts.scheme, netloc, path, parts.query, ""))


def host_of(url):
    return urlsplit(url).netloc.lower()


def split_fragment(url):
    """Return ``(url_without_fragment, fragment_with_hash_or_empty)``."""
    if "#" in url:
        base, frag = url.split("#", 1)
        return base, "#" + frag
    return url, ""


def _sanitize_segment(seg):
    seg = _ILLEGAL.sub("_", seg)
    if len(seg) > 150:
        # Keep the extension readable while bounding the length.
        head, dot, ext = seg.rpartition(".")
        digest = hashlib.sha1(seg.encode("utf-8", "replace")).hexdigest()[:8]
        if dot and len(ext) <= 12:
            seg = head[:120] + "_" + digest + "." + ext
        else:
            seg = seg[:120] + "_" + digest
    return seg


def local_path_for(url):
    """Map an absolute URL to a relative local path (posix-style).

    Everything is namespaced under the host so files from different hosts never
    collide, e.g. ``example.com/about/index.html``. Extensionless paths are
    treated as directory pages (``/about`` -> ``about/index.html``) and query
    strings are folded into a short hash suffix.
    """
    parts = urlsplit(url)
    host = (parts.netloc or "_local").lower()
    path = parts.path

    if not path or path.endswith("/"):
        path = path + "index.html"
    else:
        last = path.rsplit("/", 1)[-1]
        if "." not in last:
            path = path + "/index.html"

    segments = [
        _sanitize_segment(unquote(s))
        for s in path.split("/")
        if s not in ("", ".", "..")
    ]
    rel = posixpath.join(host, *segments) if segments else posixpath.join(host, "index.html")

    if parts.query:
        rel = _add_query_suffix(rel, parts.query)
    return rel


def _add_query_suffix(rel, query):
    digest = hashlib.sha1(query.encode("utf-8", "replace")).hexdigest()[:8]
    head, dot, ext = rel.rpartition(".")
    if dot and "/" not in ext:
        return "%s__q%s.%s" % (head, digest, ext)
    return "%s__q%s" % (rel, digest)


def relative_link(from_local, to_local):
    """Relative link from one local file to another (posix-style)."""
    from_dir = posixpath.dirname(from_local) or "."
    return posixpath.relpath(to_local, from_dir)

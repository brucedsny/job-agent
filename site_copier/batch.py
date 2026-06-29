"""Copy several sites in one run.

Each seed is crawled into the same output directory. Because files are
namespaced by host (``<out>/<host>/...``), multiple sites coexist without
colliding. A per-site manifest is written plus a combined ``index.html`` linking
to every copied site.
"""

import os

from .crawler import SiteCopier
from .urls import host_of, normalize_url


def read_url_file(path):
    """Read URLs from a file, one per line. Blank lines and ``#`` comments are
    ignored."""
    urls = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if line:
                urls.append(line)
    return urls


def copy_sites(seeds, outdir, *, verbose=True, **options):
    """Copy each seed in ``seeds`` into ``outdir``. Returns a list of
    ``(seed, host, stats)`` tuples; failed seeds have ``stats=None``."""
    os.makedirs(outdir, exist_ok=True)
    results = []
    total = len(seeds)
    for i, seed in enumerate(seeds, 1):
        norm = normalize_url(seed) or normalize_url("http://" + seed)
        host = host_of(norm) if norm else seed
        if verbose:
            print("\n=== [%d/%d] %s ===" % (i, total, seed), flush=True)
        try:
            copier = SiteCopier(
                seed,
                outdir,
                verbose=verbose,
                manifest_name="manifest-%s.json" % _safe(host),
                **options,
            )
            stats = copier.run()
            results.append((copier.seed, copier.seed_host, stats))
        except Exception as exc:  # one bad site shouldn't stop the batch
            if verbose:
                print("skip %s: %s" % (seed, exc), flush=True)
            results.append((seed, host, None))

    _write_index(outdir, results)
    if verbose:
        ok = sum(1 for _, _, s in results if s)
        print("\nbatch done: %d/%d sites copied -> %s" % (ok, total, outdir), flush=True)
    return results


def _safe(host):
    return "".join(c if c.isalnum() or c in ".-" else "_" for c in host)


def _write_index(outdir, results):
    rows = []
    for seed, host, stats in results:
        if stats is None:
            rows.append('<li><s>%s</s> — failed</li>' % _esc(seed))
            continue
        rows.append(
            '<li><a href="%s/index.html">%s</a> — %d pages, %d assets</li>'
            % (_esc(host), _esc(host), stats.pages, stats.assets)
        )
    html = (
        "<!doctype html><meta charset=utf-8><title>Sites copiados</title>"
        "<h1>Sites copiados</h1><ul>%s</ul>" % "".join(rows)
    )
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)


def _esc(s):
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )

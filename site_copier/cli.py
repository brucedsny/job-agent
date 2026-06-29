"""Command-line interface for site_copier."""

import argparse
import sys

from . import __version__
from .crawler import DEFAULT_UA, SiteCopier


def build_parser():
    p = argparse.ArgumentParser(
        prog="site-copier",
        description="Copy an entire website for offline browsing.",
    )
    p.add_argument(
        "url", nargs="*",
        help="one or more seed URLs to copy (each into <out>/<host>/)",
    )
    p.add_argument(
        "-i", "--urls-file", metavar="FILE",
        help="file with one URL per line ('#' comments allowed)",
    )
    p.add_argument(
        "-o", "--out", default="site-copy",
        help="output directory (default: ./site-copy)",
    )
    p.add_argument(
        "--max-pages", type=int, default=500,
        help="maximum number of HTML pages to download (default: 500)",
    )
    p.add_argument(
        "--max-depth", type=int, default=10,
        help="maximum link depth from the seed (default: 10)",
    )
    p.add_argument(
        "--workers", type=int, default=4,
        help="number of concurrent download workers (default: 4)",
    )
    p.add_argument(
        "--delay", type=float, default=0.0,
        help="seconds to wait after each request, per worker (default: 0)",
    )
    p.add_argument(
        "--timeout", type=float, default=30,
        help="per-request timeout in seconds (default: 30)",
    )
    p.add_argument(
        "--same-host-assets", action="store_true",
        help="only download assets hosted on the seed's domain",
    )
    p.add_argument(
        "--allow-host", action="append", default=None, metavar="HOST",
        help="extra host whose pages may be crawled (repeatable)",
    )
    p.add_argument(
        "--respect-robots", action="store_true",
        help="obey the site's robots.txt rules",
    )
    p.add_argument(
        "--user-agent", default=DEFAULT_UA, help="User-Agent header to send",
    )
    p.add_argument("-q", "--quiet", action="store_true", help="suppress progress output")
    p.add_argument("--version", action="version", version="site-copier " + __version__)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    seeds = list(args.url)
    if args.urls_file:
        from .batch import read_url_file

        try:
            seeds += read_url_file(args.urls_file)
        except OSError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 2
    if not seeds:
        parser.error("provide at least one URL, or --urls-file FILE")

    options = dict(
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        cross_host_assets=not args.same_host_assets,
        delay=args.delay,
        workers=args.workers,
        timeout=args.timeout,
        user_agent=args.user_agent,
        respect_robots=args.respect_robots,
    )

    try:
        if len(seeds) == 1:
            return _run_single(seeds[0], args, options)
        return _run_batch(seeds, args, options)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


def _run_single(seed, args, options):
    allowed = None
    if args.allow_host:
        from .urls import host_of, normalize_url

        norm = normalize_url(seed) or normalize_url("http://" + seed)
        allowed = [host_of(norm)] + [h.lower() for h in args.allow_host] if norm else None

    try:
        copier = SiteCopier(seed, args.out, allowed_hosts=allowed,
                            verbose=not args.quiet, **options)
        stats = copier.run()
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 1 if stats.pages == 0 else 0


def _run_batch(seeds, args, options):
    from .batch import copy_sites

    results = copy_sites(seeds, args.out, verbose=not args.quiet, **options)
    return 0 if any(stats for _, _, stats in results) else 1


if __name__ == "__main__":
    sys.exit(main())

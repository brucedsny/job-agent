"""Extracting links/assets from HTML & CSS, and rewriting them for offline use.

Discovery is tag-aware (via :class:`html.parser.HTMLParser`) so we can tell page
links (which we recurse into) from assets (which we just download). Rewriting is
tag-agnostic and regex-based over the raw text, so the original formatting of
the document is preserved.
"""

import re
from html.parser import HTMLParser
from urllib.parse import urljoin

# Tags whose URL points at another *page* to follow and recurse into.
PAGE_TAGS = {"a": "href", "area": "href", "iframe": "src", "frame": "src"}

# Tags whose URL points at an *asset* to download (but not recurse into).
ASSET_ATTRS = {
    "img": ["src", "data-src", "data-original"],
    "script": ["src"],
    "link": ["href"],
    "source": ["src"],
    "video": ["src", "poster"],
    "audio": ["src"],
    "embed": ["src"],
    "object": ["data"],
    "track": ["src"],
    "input": ["src"],
}

_CSS_URL_RE = re.compile(r"""url\(\s*(?P<q>["']?)(?P<url>[^"')]+?)(?P=q)\s*\)""", re.I)
_CSS_IMPORT_RE = re.compile(r"""@import\s+(?P<q>["'])(?P<url>[^"']+)(?P=q)""", re.I)

# URL-bearing HTML attributes, for the rewrite pass.
_ATTR_RE = re.compile(
    r"""(?P<pre>\b(?:href|src|poster|data-src|data-original|data-href|action|data)\s*=\s*)"""
    r"""(?P<q>["'])(?P<url>[^"']*)(?P=q)""",
    re.I,
)
_SRCSET_RE = re.compile(
    r"""(?P<pre>\bsrcset\s*=\s*)(?P<q>["'])(?P<val>[^"']*)(?P=q)""", re.I
)


def parse_srcset(value):
    """Yield the URL part of each candidate in a ``srcset`` attribute."""
    for candidate in value.split(","):
        candidate = candidate.strip()
        if candidate:
            yield candidate.split()[0]


def css_urls(text):
    """All URLs referenced from a chunk of CSS (``url(...)`` and ``@import``)."""
    out = []
    for m in _CSS_URL_RE.finditer(text):
        out.append(m.group("url").strip())
    for m in _CSS_IMPORT_RE.finditer(text):
        out.append(m.group("url").strip())
    return out


class _Extractor(HTMLParser):
    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.pages = []
        self.assets = []
        self._in_style = False
        self._style_buf = []

    def _add(self, bucket, raw):
        raw = (raw or "").strip()
        if raw:
            bucket.append(urljoin(self.base, raw))

    def handle_starttag(self, tag, attrs):
        d = {k.lower(): (v or "") for k, v in attrs}

        if tag in PAGE_TAGS:
            self._add(self.pages, d.get(PAGE_TAGS[tag]))

        for attr in ASSET_ATTRS.get(tag, ()):
            self._add(self.assets, d.get(attr))
        if tag in ASSET_ATTRS and d.get("srcset"):
            for u in parse_srcset(d["srcset"]):
                self._add(self.assets, u)

        if d.get("style"):
            for u in css_urls(d["style"]):
                self._add(self.assets, u)

        if tag == "style":
            self._in_style = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False
            for u in css_urls("".join(self._style_buf)):
                self._add(self.assets, u)
            self._style_buf = []

    def handle_data(self, data):
        if self._in_style:
            self._style_buf.append(data)


def extract_html(text, base_url):
    """Return ``(page_urls, asset_urls)`` as absolute URLs."""
    parser = _Extractor(base_url)
    try:
        parser.feed(text)
        parser.close()
    except Exception:
        # Malformed markup shouldn't abort a crawl; return whatever we gathered.
        pass
    return parser.pages, parser.assets


def extract_css(text, base_url):
    """Return asset URLs referenced from a CSS document (absolute)."""
    return [urljoin(base_url, u) for u in css_urls(text)]


def rewrite_html(text, base_url, mapper):
    text = _ATTR_RE.sub(lambda m: _sub_attr(m, base_url, mapper), text)
    text = _SRCSET_RE.sub(lambda m: _sub_srcset(m, base_url, mapper), text)
    return rewrite_css(text, base_url, mapper)


def rewrite_css(text, base_url, mapper):
    text = _CSS_URL_RE.sub(lambda m: _sub_css_url(m, base_url, mapper), text)
    text = _CSS_IMPORT_RE.sub(lambda m: _sub_css_import(m, base_url, mapper), text)
    return text


def _resolve(raw, base_url, mapper):
    """Return the rewritten URL, or ``None`` to leave the original untouched."""
    raw = raw.strip()
    if not raw or raw.startswith(("data:", "#", "mailto:", "tel:", "javascript:")):
        return None
    return mapper(urljoin(base_url, raw))


def _sub_attr(m, base_url, mapper):
    new = _resolve(m.group("url"), base_url, mapper)
    if new is None:
        return m.group(0)
    return "%s%s%s%s" % (m.group("pre"), m.group("q"), new, m.group("q"))


def _sub_srcset(m, base_url, mapper):
    out = []
    for candidate in m.group("val").split(","):
        candidate = candidate.strip()
        if not candidate:
            continue
        bits = candidate.split()
        new = _resolve(bits[0], base_url, mapper)
        if new is not None:
            bits[0] = new
        out.append(" ".join(bits))
    return "%s%s%s%s" % (m.group("pre"), m.group("q"), ", ".join(out), m.group("q"))


def _sub_css_url(m, base_url, mapper):
    new = _resolve(m.group("url"), base_url, mapper)
    if new is None:
        return m.group(0)
    return "url(%s%s%s)" % (m.group("q"), new, m.group("q"))


def _sub_css_import(m, base_url, mapper):
    new = _resolve(m.group("url"), base_url, mapper)
    if new is None:
        return m.group(0)
    return '@import "%s"' % new

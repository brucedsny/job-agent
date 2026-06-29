import unittest

from site_copier import extract


class ExtractHtmlTests(unittest.TestCase):
    def test_separates_pages_and_assets(self):
        html = """
        <a href="/about">About</a>
        <img src="/img/logo.png">
        <link rel="stylesheet" href="style.css">
        <script src="app.js"></script>
        """
        pages, assets = extract.extract_html(html, "http://x.com/")
        self.assertIn("http://x.com/about", pages)
        self.assertIn("http://x.com/img/logo.png", assets)
        self.assertIn("http://x.com/style.css", assets)
        self.assertIn("http://x.com/app.js", assets)

    def test_srcset(self):
        html = '<img srcset="a.png 1x, b.png 2x">'
        _, assets = extract.extract_html(html, "http://x.com/")
        self.assertIn("http://x.com/a.png", assets)
        self.assertIn("http://x.com/b.png", assets)

    def test_inline_and_block_style(self):
        html = (
            '<div style="background:url(bg.png)"></div>'
            "<style>@import 'theme.css'; .a{background:url(\"x.png\")}</style>"
        )
        _, assets = extract.extract_html(html, "http://x.com/")
        self.assertIn("http://x.com/bg.png", assets)
        self.assertIn("http://x.com/theme.css", assets)
        self.assertIn("http://x.com/x.png", assets)


class ExtractCssTests(unittest.TestCase):
    def test_urls_and_imports(self):
        css = "@import 'base.css'; .a{background:url(../img/p.png)}"
        assets = extract.extract_css(css, "http://x.com/css/main.css")
        self.assertIn("http://x.com/css/base.css", assets)
        self.assertIn("http://x.com/img/p.png", assets)


class RewriteTests(unittest.TestCase):
    def _mapper(self, mapping):
        def m(url):
            return mapping.get(url, url)
        return m

    def test_rewrites_known_urls_to_local(self):
        html = '<a href="/about">x</a><img src="/logo.png">'
        mapper = self._mapper({
            "http://x.com/about": "about/index.html",
            "http://x.com/logo.png": "logo.png",
        })
        out = extract.rewrite_html(html, "http://x.com/", mapper)
        self.assertIn('href="about/index.html"', out)
        self.assertIn('src="logo.png"', out)

    def test_leaves_special_schemes(self):
        html = '<a href="mailto:a@b.com">m</a><a href="#top">t</a>'
        out = extract.rewrite_html(html, "http://x.com/", self._mapper({}))
        self.assertIn('href="mailto:a@b.com"', out)
        self.assertIn('href="#top"', out)

    def test_rewrites_css_url(self):
        css = ".a{background:url(/img/p.png)}"
        mapper = self._mapper({"http://x.com/img/p.png": "../img/p.png"})
        out = extract.rewrite_css(css, "http://x.com/css/main.css", mapper)
        self.assertIn("url(../img/p.png)", out)


if __name__ == "__main__":
    unittest.main()

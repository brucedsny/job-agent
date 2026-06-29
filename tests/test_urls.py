import unittest

from site_copier.urls import (
    local_path_for,
    normalize_url,
    relative_link,
    split_fragment,
)


class NormalizeTests(unittest.TestCase):
    def test_drops_fragment(self):
        self.assertEqual(
            normalize_url("http://x.com/a#frag"), "http://x.com/a"
        )

    def test_resolves_relative(self):
        self.assertEqual(
            normalize_url("../b", base="http://x.com/a/c"), "http://x.com/b"
        )

    def test_rejects_non_http(self):
        self.assertIsNone(normalize_url("mailto:a@b.com"))
        self.assertIsNone(normalize_url("javascript:void(0)"))
        self.assertIsNone(normalize_url("data:image/png;base64,AAAA"))

    def test_lowercases_host(self):
        self.assertEqual(normalize_url("http://X.COM/A"), "http://x.com/A")

    def test_preserves_trailing_slash(self):
        self.assertEqual(normalize_url("http://x.com/a/"), "http://x.com/a/")


class LocalPathTests(unittest.TestCase):
    def test_root_becomes_index(self):
        self.assertEqual(local_path_for("http://x.com/"), "x.com/index.html")

    def test_extensionless_is_directory_page(self):
        self.assertEqual(
            local_path_for("http://x.com/about"), "x.com/about/index.html"
        )

    def test_keeps_extension(self):
        self.assertEqual(
            local_path_for("http://x.com/style.css"), "x.com/style.css"
        )

    def test_namespaces_by_host(self):
        self.assertTrue(local_path_for("http://cdn.io/a.js").startswith("cdn.io/"))

    def test_query_gets_hash_suffix(self):
        a = local_path_for("http://x.com/p.html?v=1")
        b = local_path_for("http://x.com/p.html?v=2")
        self.assertNotEqual(a, b)
        self.assertTrue(a.endswith(".html"))


class RelativeLinkTests(unittest.TestCase):
    def test_sibling(self):
        self.assertEqual(
            relative_link("x.com/a/index.html", "x.com/a/style.css"), "style.css"
        )

    def test_up_and_over(self):
        self.assertEqual(
            relative_link("x.com/a/b/index.html", "x.com/c.js"), "../../c.js"
        )


class FragmentTests(unittest.TestCase):
    def test_split(self):
        self.assertEqual(split_fragment("http://x.com/a#s"), ("http://x.com/a", "#s"))
        self.assertEqual(split_fragment("http://x.com/a"), ("http://x.com/a", ""))


if __name__ == "__main__":
    unittest.main()

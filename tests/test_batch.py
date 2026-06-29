import os
import tempfile
import unittest

from site_copier import batch


class ReadUrlFileTests(unittest.TestCase):
    def test_skips_blanks_and_comments(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "urls.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("http://a.com\n\n# a comment\nhttp://b.com  # inline\n")
            self.assertEqual(
                batch.read_url_file(path), ["http://a.com", "http://b.com"]
            )


class IndexTests(unittest.TestCase):
    def test_writes_index_with_links_and_failures(self):
        class FakeStats:
            pages = 3
            assets = 5

        with tempfile.TemporaryDirectory() as d:
            results = [
                ("http://a.com/", "a.com", FakeStats()),
                ("http://b.com/", "b.com", None),
            ]
            batch._write_index(d, results)
            with open(os.path.join(d, "index.html"), encoding="utf-8") as fh:
                html = fh.read()
            self.assertIn('href="a.com/index.html"', html)
            self.assertIn("3 pages, 5 assets", html)
            self.assertIn("failed", html)


if __name__ == "__main__":
    unittest.main()

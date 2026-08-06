from html.parser import HTMLParser
import pathlib
import unittest

ROOT = pathlib.Path(__file__).parents[1]
SITE = ROOT / "site"


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.forms = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.add(values["id"])
        if tag == "a" and "href" in values:
            self.links.append(values["href"])
        if tag == "form":
            self.forms.append(values)
        if tag == "img":
            self.images.append(values)


class StaticSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = SiteParser()
        cls.parser.feed((SITE / "index.html").read_text())

    def test_main_navigation_targets_exist(self):
        fragment_links = {link[1:] for link in self.parser.links if link.startswith("#")}
        self.assertTrue(fragment_links.issubset(self.parser.ids))

    def test_contact_form_and_accessible_images_exist(self):
        self.assertEqual(len(self.parser.forms), 1)
        self.assertTrue(all("alt" in image for image in self.parser.images))

    def test_local_image_assets_exist(self):
        for image in self.parser.images:
            source = image.get("src", "")
            if source.startswith("/"):
                self.assertTrue((SITE / source.lstrip("/")).is_file(), source)

    def test_internal_root_links_resolve_to_files(self):
        for link in self.parser.links:
            if not link.startswith("/") or link == "/":
                continue
            path = link.split("#", 1)[0]
            target = SITE / path.lstrip("/")
            if path.endswith("/"):
                target = target / "index.html"
            self.assertTrue(target.exists(), f"Broken internal link: {link}")

    def test_legal_pages_and_operational_files_exist(self):
        expected = [
            "privacy-policy/index.html",
            "terms-and-conditions/index.html",
            "disclaimer/index.html",
            "copyright-notice/index.html",
            "404.html",
            "robots.txt",
            "sitemap.xml",
        ]
        for relative in expected:
            self.assertTrue((SITE / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()

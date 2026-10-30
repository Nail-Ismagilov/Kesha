import os
import tempfile
import unittest

from dogwatch.checks.photo_count import check_photo_count, count_local_photos
from dogwatch.context import Context
from dogwatch.models import DogRef
from dogwatch.page import PageData
from dogwatch.store import Store


def urls(n):
    return [f"https://x.test/{i}.jpg" for i in range(1, n + 1)]


class PhotoCount(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = self.tmp.name
        self.dog = DogRef(key="H/nera", name="nera", url="u", folder=self.folder)
        self.ctx = Context(Store())

    def tearDown(self):
        self.tmp.cleanup()

    def touch(self, *names):
        for n in names:
            open(os.path.join(self.folder, n), "wb").close()

    def check(self, n_site):
        return check_photo_count(self.dog, PageData("x", urls(n_site)), self.ctx)

    def test_equal_counts_no_finding(self):
        self.touch("nera1.jpg", "nera2.jpg", "nera3.jpg")
        self.assertEqual(self.check(3), [])

    def test_fewer_local_photos(self):
        self.touch("nera1.jpg", "nera2.jpg")
        f = self.check(4)
        self.assertEqual([(x.kind, x.detail) for x in f], [("photo_count", "4 online / 2 lokal")])

    def test_more_local_photos(self):
        self.touch("nera1.jpg", "nera2.jpg", "nera3.jpg")
        f = self.check(1)
        self.assertEqual([(x.kind, x.detail) for x in f], [("photo_count", "1 online / 3 lokal")])

    def test_other_files_are_not_counted(self):
        self.touch("nera1.jpg", "nera.txt", "fingerprint.json", "cover.jpg", "other1.jpg", "nera_edit.jpg")
        self.assertEqual(self.check(1), [])

    def test_extensions_and_case(self):
        self.touch("nera1.JPG", "nera2.jpeg", "nera3.png", "nera4.webp", "nera5.gif", "nera6.bmp")
        self.assertEqual(count_local_photos(self.folder, "nera"), 5)

    def test_name_with_regex_characters(self):
        dog = DogRef(key="k", name="a.b+c", url="u", folder=self.folder)
        self.touch("a.b+c1.jpg", "axb+c2.jpg")
        self.assertEqual(count_local_photos(self.folder, dog.name), 1)

    def test_empty_gallery_gets_a_hint(self):
        self.touch("nera1.jpg")
        f = self.check(0)
        self.assertEqual(f[0].kind, "photo_count")
        self.assertIn("0 online / 1 lokal", f[0].detail)
        self.assertIn("Galerie", f[0].detail)

    def test_no_folder_is_skipped_and_missing_folder_counts_zero(self):
        no_folder = DogRef(key="k", name="nera", url="u", folder="")
        self.assertEqual(check_photo_count(no_folder, PageData("x", urls(3)), self.ctx), [])
        gone = DogRef(key="k", name="nera", url="u", folder=os.path.join(self.folder, "missing"))
        f = check_photo_count(gone, PageData("x", urls(2)), self.ctx)
        self.assertEqual(f[0].detail, "2 online / 0 lokal")


if __name__ == "__main__":
    unittest.main()

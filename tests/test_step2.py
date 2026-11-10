import io
import os
import random
import tempfile
import unittest

from dogwatch.checks.first_photo import check_first_photo
from dogwatch.context import Context
from dogwatch.imagecmp import dhash, same_picture
from dogwatch.models import DogRef
from dogwatch.page import PageData
from dogwatch.runner import run
from dogwatch.store import Store

try:
    from PIL import Image
    HAVE_PIL = True
except Exception:        # pragma: no cover
    HAVE_PIL = False


def make_jpeg(seed, quality=90, size=(96, 96)):
    """A deterministic 'photo': smooth random blobs, saved as JPEG bytes."""
    rnd = random.Random(seed)
    img = Image.new("RGB", (8, 8))
    img.putdata([(rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)) for _ in range(64)])
    img = img.resize(size, Image.BICUBIC)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


class Fakes:
    """Replaces the network. size=None means: server sends no Content-Length."""
    def __init__(self, data, size="auto", fail=False):
        self.data, self.fail, self.downloads = data, fail, 0
        self._size = len(data) if size == "auto" else size

    def head_size(self, url):
        return self._size

    def get_bytes(self, url):
        self.downloads += 1
        if self.fail:
            raise IOError("boom")
        return self.data


class FirstPhoto(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = self.tmp.name
        self.dog = DogRef(key="H/nera", name="nera", url="https://x.test/nera/", folder=self.folder)
        self.page = PageData(description="x", photo_urls=["https://x.test/1.jpg", "https://x.test/2.jpg"])

    def tearDown(self):
        self.tmp.cleanup()

    def put_local(self, data):
        with open(os.path.join(self.folder, "nera1.jpg"), "wb") as f:
            f.write(data)

    def ctx(self, fakes):
        return Context(Store(), head_size=fakes.head_size, get_bytes=fakes.get_bytes)

    def test_same_size_means_unchanged_and_no_download(self):
        data = b"A" * 1000
        self.put_local(data)
        fk = Fakes(data)
        self.assertEqual(check_first_photo(self.dog, self.page, self.ctx(fk)), [])
        self.assertEqual(fk.downloads, 0)

    def test_unknown_size_but_identical_bytes(self):
        data = b"B" * 500
        self.put_local(data)
        fk = Fakes(data, size=None)
        self.assertEqual(check_first_photo(self.dog, self.page, self.ctx(fk)), [])
        self.assertEqual(fk.downloads, 1)

    def test_missing_local_file(self):
        f = check_first_photo(self.dog, self.page, self.ctx(Fakes(b"x")))
        self.assertEqual([(x.kind, x.detail) for x in f], [("first_photo", "1. Foto fehlt lokal")])

    def test_no_folder_or_no_photos_means_no_check(self):
        no_folder = DogRef(key="k", name="nera", url="u", folder="")
        self.assertEqual(check_first_photo(no_folder, self.page, self.ctx(Fakes(b"x"))), [])
        self.assertEqual(check_first_photo(self.dog, PageData("x", []), self.ctx(Fakes(b"x"))), [])

    def test_download_failure_is_a_warning_not_a_change(self):
        self.put_local(b"old-old-old")
        f = check_first_photo(self.dog, self.page, self.ctx(Fakes(b"new", fail=True)))
        self.assertEqual([x.kind for x in f], ["warning"])

    @unittest.skipUnless(HAVE_PIL, "Pillow not installed")
    def test_different_picture_is_reported(self):
        self.put_local(make_jpeg(1))
        f = check_first_photo(self.dog, self.page, self.ctx(Fakes(make_jpeg(2))))
        self.assertEqual([(x.kind, x.detail) for x in f], [("first_photo", "1. Foto geändert")])

    @unittest.skipUnless(HAVE_PIL, "Pillow not installed")
    def test_reencoded_same_picture_is_not_reported(self):
        self.put_local(make_jpeg(1, quality=95))
        fk = Fakes(make_jpeg(1, quality=60))           # different bytes, same picture
        self.assertNotEqual(fk.data, make_jpeg(1, quality=95))
        self.assertEqual(check_first_photo(self.dog, self.page, self.ctx(fk)), [])

    @unittest.skipUnless(HAVE_PIL, "Pillow not installed")
    def test_bad_image_data_counts_as_changed(self):
        self.put_local(make_jpeg(1))
        f = check_first_photo(self.dog, self.page, self.ctx(Fakes(b"not an image at all", size=None)))
        self.assertEqual([x.kind for x in f], ["first_photo"])


class ImageCompare(unittest.TestCase):
    def test_identical_bytes(self):
        self.assertTrue(same_picture(b"abc", b"abc"))

    def test_different_bytes_without_decodable_image(self):
        self.assertFalse(same_picture(b"abc", b"abd"))
        self.assertIsNone(dhash(b"abc"))

    @unittest.skipUnless(HAVE_PIL, "Pillow not installed")
    def test_dhash_is_stable_under_recompression(self):
        a, b = dhash(make_jpeg(7, quality=95)), dhash(make_jpeg(7, quality=50))
        self.assertLessEqual(bin(a ^ b).count("1"), 10)
        c = dhash(make_jpeg(8))
        self.assertGreater(bin(a ^ c).count("1"), 10)


class RunnerIntegration(unittest.TestCase):
    def test_runner_routes_first_photo_findings_and_warnings(self):
        with tempfile.TemporaryDirectory() as folder:
            with open(os.path.join(folder, "nera1.jpg"), "wb") as f:
                f.write(b"local-photo")
            dog = DogRef(key="H/nera", name="nera", url="https://x.test/nera/", folder=folder)
            html = ('<div id="page-content"><p>Text.</p><div class="gal-container">'
                    '<div class="img-box-shadow"><a href="https://x.test/1.jpg"></a></div></div></div>')
            fk = Fakes(b"site-photo-different-size")
            res = run([dog], Store(), fetch=lambda u: html,
                      head_size=fk.head_size, get_bytes=fk.get_bytes)
            kinds = [f.kind for f in res.findings]
            self.assertEqual(res.baselined, 1)
            self.assertEqual(kinds, ["first_photo"] if not HAVE_PIL else ["first_photo"])
            fk2 = Fakes(b"x", fail=True, size=None)
            res2 = run([dog], Store(), fetch=lambda u: html,
                       head_size=fk2.head_size, get_bytes=fk2.get_bytes)
            self.assertEqual([w.kind for w in res2.warnings], ["warning"])
            self.assertEqual(res2.findings, [])


if __name__ == "__main__":
    unittest.main()

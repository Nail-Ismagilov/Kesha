import os
import tempfile
import threading
import time
import unittest
from hashlib import md5
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ["NO_PROXY"] = "127.0.0.1,localhost," + os.environ.get("NO_PROXY", "")

from dogwatch import http
from dogwatch.models import DogRef
from dogwatch.runner import run
from dogwatch.store import Store

PHOTOS_PER_DOG = 2


def photo_bytes(i, k):
    return (f"IMG-{i}-{k}-".encode()) * 40


class Site:
    """A tiny local 'shelter website' with counters, optional latency and ETags."""

    def __init__(self, n, delay=0.0, etag=True):
        self.n, self.delay, self.etag = n, delay, etag
        self.prices = {i: 490 for i in range(n)}
        self.lock = threading.Lock()
        self.page_requests = self.page_304 = self.image_gets = self.image_heads = 0
        self.active = self.max_active = 0
        self.port = None

    def html(self, i):
        links = "".join(
            f'<div class="img-box-shadow"><a href="http://127.0.0.1:{self.port}/img/{i}/{k}.jpg"></a></div>'
            for k in range(1, PHOTOS_PER_DOG + 1))
        return (f'<html><body><div id="page-content"><h2>Dog {i}</h2>'
                f'<p>Schutzgebühr: {self.prices[i]} EUR</p><p>Lieb und verspielt.</p>'
                f'<div class="gal-container">{links}</div>'
                f'<p>Sie wird nach positiver Vorkontrolle vermittelt.</p></div></body></html>')

    def url(self, i):
        return f"http://127.0.0.1:{self.port}/dog/{i}"


def make_handler(site):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body=b"", headers=None, head_only=False, length=None):
            self.send_response(code)
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body) if length is None else length))
            self.end_headers()
            if not head_only:
                self.wfile.write(body)

        def _serve(self, head_only):
            parts = self.path.strip("/").split("/")
            if parts[0] == "dog":
                with site.lock:
                    site.active += 1
                    site.max_active = max(site.max_active, site.active)
                    site.page_requests += 1
                try:
                    if site.delay:
                        time.sleep(site.delay)
                    body = site.html(int(parts[1])).encode("utf-8")
                    headers = {"Content-Type": "text/html; charset=utf-8"}
                    if site.etag:
                        tag = '"' + md5(body).hexdigest() + '"'
                        headers["ETag"] = tag
                        if self.headers.get("If-None-Match") == tag:
                            with site.lock:
                                site.page_304 += 1
                            return self._send(304, b"", {"ETag": tag})
                    self._send(200, body, headers)
                finally:
                    with site.lock:
                        site.active -= 1
            elif parts[0] == "img":
                data = photo_bytes(int(parts[1]), int(parts[2].split(".")[0]))
                with site.lock:
                    if head_only:
                        site.image_heads += 1
                    else:
                        site.image_gets += 1
                self._send(200, data, {"Content-Type": "image/jpeg"}, head_only=head_only,
                           length=len(data))
            else:
                self._send(404)

        def do_GET(self):
            self._serve(False)

        def do_HEAD(self):
            self._serve(True)
    return H


class LocalSiteTestCase(unittest.TestCase):
    N = 12

    def start(self, **kw):
        self.site = Site(self.N, **kw)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.site))
        self.site.port = self.server.server_port
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dogs = []
        for i in range(self.N):
            folder = os.path.join(self.tmp.name, f"dog{i}")
            os.makedirs(folder)
            for k in range(1, PHOTOS_PER_DOG + 1):
                with open(os.path.join(folder, f"dog{i}{k}.jpg"), "wb") as f:
                    f.write(photo_bytes(i, k))
            self.dogs.append(DogRef(key=f"H/dog{i}", name=f"dog{i}", url=self.site.url(i), folder=folder))
        self.store = Store()


class Speed(LocalSiteTestCase):
    def test_workers_are_much_faster_than_sequential(self):
        self.start(delay=0.06, etag=False)
        seq = run(self.dogs, Store(), workers=1)
        par = run(self.dogs, Store(), workers=8)
        self.assertEqual((seq.checked, par.checked), (self.N, self.N))
        self.assertEqual(len(seq.errors) + len(par.errors), 0)
        self.assertGreater(self.site.max_active, 1)                 # really concurrent
        self.assertLess(par.seconds, seq.seconds / 2.5,
                        f"sequential {seq.seconds:.2f}s vs parallel {par.seconds:.2f}s")

    def test_same_result_sequential_and_parallel_and_input_order(self):
        self.start(etag=False)
        run(self.dogs, self.store, workers=1)                       # baseline
        for i in (2, 5, 9):
            self.site.prices[i] = 590
        a = run(self.dogs, self.store, workers=1)
        # restore the baseline in a second store for the parallel run
        store2 = Store()
        for i in (2, 5, 9):
            self.site.prices[i] = 490
        run(self.dogs, store2, workers=1)
        for i in (2, 5, 9):
            self.site.prices[i] = 590
        b = run(self.dogs, store2, workers=8)
        key = lambda r: [(f.dog.key, f.kind, f.detail) for f in r.findings]
        self.assertEqual(key(a), key(b))
        self.assertEqual([k[0] for k in key(b)], ["H/dog2", "H/dog5", "H/dog9"])

    def test_progress_is_reported_once_per_dog(self):
        self.start(etag=False)
        seen = []
        run(self.dogs, self.store, workers=6, on_progress=lambda d, t: seen.append((d, t)))
        self.assertEqual(seen, [(i, self.N) for i in range(1, self.N + 1)])


class Cache(LocalSiteTestCase):
    def test_unchanged_pages_are_answered_with_304(self):
        self.start(etag=True)
        r1 = run(self.dogs, self.store)
        self.assertEqual((r1.baselined, r1.cached, self.site.page_304), (self.N, 0, 0))
        r2 = run(self.dogs, self.store)
        self.assertEqual((r2.cached, self.site.page_304), (self.N, self.N))
        self.assertEqual((r2.findings, r2.errors, r2.warnings), ([], [], []))

    def test_changed_page_is_detected_the_others_stay_cached(self):
        self.start(etag=True)
        run(self.dogs, self.store)
        self.site.prices[3] = 650
        r = run(self.dogs, self.store)
        self.assertEqual([(f.dog.key, f.kind, f.detail) for f in r.findings],
                         [("H/dog3", "price", "490 \u2192 650 EUR")])
        self.assertEqual(r.cached, self.N - 1)

    def test_local_changes_are_found_even_when_the_page_is_cached(self):
        self.start(etag=True)
        run(self.dogs, self.store)
        os.remove(os.path.join(self.dogs[5].folder, "dog52.jpg"))          # delete one photo
        with open(os.path.join(self.dogs[6].folder, "dog61.jpg"), "wb") as f:
            f.write(b"someone replaced the first photo")                   # replace first photo
        r = run(self.dogs, self.store)
        self.assertEqual(r.cached, self.N)                                 # pages: all 304
        got = sorted((f.dog.key, f.kind) for f in r.findings)
        self.assertEqual(got, [("H/dog5", "photo_count"), ("H/dog6", "first_photo")])

    def test_no_cache_option_always_fetches_the_page(self):
        self.start(etag=True)
        run(self.dogs, self.store, use_cache=False)
        r = run(self.dogs, self.store, use_cache=False)
        self.assertEqual((r.cached, self.site.page_304), (0, 0))

    def test_server_without_etag_still_works(self):
        self.start(etag=False)
        run(self.dogs, self.store)
        r = run(self.dogs, self.store)
        self.assertEqual((r.cached, len(r.errors), len(r.findings)), (0, 0, 0))


class PhotoTraffic(LocalSiteTestCase):
    def test_unchanged_photos_cost_only_head_requests(self):
        self.start(etag=True)
        run(self.dogs, self.store)
        run(self.dogs, self.store)
        self.assertEqual(self.site.image_gets, 0)                  # nothing downloaded
        self.assertGreaterEqual(self.site.image_heads, 2 * self.N)  # one HEAD per dog and run


class ErrorsAndLimits(LocalSiteTestCase):
    def test_one_dead_dog_does_not_stop_the_run(self):
        self.start(etag=True)
        dogs = self.dogs + [DogRef(key="H/dead", name="dead", url=f"http://127.0.0.1:{self.site.port}/nothing/1")]
        r = run(dogs, self.store, workers=4)
        self.assertEqual((r.checked, len(r.errors)), (self.N, 1))
        self.assertEqual(r.errors[0].dog.key, "H/dead")

    def test_workers_larger_than_dog_count(self):
        self.start(etag=True)
        r = run(self.dogs[:2], self.store, workers=50)
        self.assertEqual(r.checked, 2)

    def test_empty_dog_list(self):
        self.start(etag=True)
        r = run([], self.store)
        self.assertEqual((r.checked, r.findings), (0, []))


class HttpHelpers(LocalSiteTestCase):
    def test_head_size_and_get_bytes(self):
        self.start(etag=True)
        url = f"http://127.0.0.1:{self.site.port}/img/1/1.jpg"
        self.assertEqual(http.head_size(url), len(photo_bytes(1, 1)))
        self.assertEqual(http.get_bytes(url), photo_bytes(1, 1))
        self.assertIsNone(http.head_size("http://127.0.0.1:1/unreachable.jpg"))
        with self.assertRaises(Exception):
            http.get_bytes(f"http://127.0.0.1:{self.site.port}/dog/1")     # html, not an image


if __name__ == "__main__":
    unittest.main()

import unittest

from dogwatch.checks.description import check_description, parse_price, text_hash
from dogwatch.models import DogRef
from dogwatch.page import parse_page
from dogwatch.runner import run
from dogwatch.store import Store

HTML = """
<html><body><div id="page-content">
<h2>Nera</h2>
<p><strong>Name</strong>: Nera</p>
<p><strong>Schutzgeb\u00fchr:</strong> {price}</p>
<p>Nera ist geimpft, gechipt, entwurmt und besitzt einen internationalen Pass.{extra}</p>
<div class="gal-container">
  <div class="img-box-shadow"><a href="https://x.test/1.jpg"><img src="t1.jpg"></a></div>
  <div class="img-box-shadow"><a href="https://x.test/2.jpg"><img src="t2.jpg"></a></div>
</div>
<p>Sie wird nach positiver Vorkontrolle mit Schutzvertrag vermittelt. BOILERPLATE {boiler}</p>
</div></body></html>
"""

def page(price="490 EUR", extra="", boiler="v1"):
    return HTML.format(price=price, extra=extra, boiler=boiler)

DOG = DogRef(key="H/nera", name="nera", url="https://x.test/nera/")


class PriceParsing(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(parse_price("Schutzgeb\u00fchr: 590 EUR"), 590.0)
        self.assertEqual(parse_price("Schutzgeb\u00fchr: 790,00 EUR"), 790.0)
        self.assertEqual(parse_price("Schutzgeb\u00fchr 1.200,50 \u20ac"), 1200.5)
        self.assertEqual(parse_price("Schutzgeb\u00fcr: 490 \u20ac"), 490.0)   # typo variant
        self.assertIsNone(parse_price("kein Preis"))


class PageParsing(unittest.TestCase):
    def test_photos_description_boilerplate(self):
        p = parse_page(page())
        self.assertEqual(p.photo_urls, ["https://x.test/1.jpg", "https://x.test/2.jpg"])
        self.assertIn("Schutzgeb\u00fchr: 490 EUR", p.description)
        self.assertNotIn("BOILERPLATE", p.description)
        self.assertNotIn("x.test", p.description)

    def test_missing_content_raises(self):
        with self.assertRaises(Exception):
            parse_page("<html><body>nothing</body></html>")

    def test_price_behind_marker_is_kept(self):
        html = ('<div id="page-content"><p>Text.</p><p>Sie wird nach positiver Vorkontrolle '
                'vermittelt.</p><p>Schutzgeb\u00fchr: 590 EUR</p></div>')
        self.assertEqual(parse_price(parse_page(html).description), 590.0)


class DescriptionCheck(unittest.TestCase):
    def setUp(self):
        self.store = Store()

    def run_check(self, html):
        return check_description(DOG, parse_page(html), self.store)

    def test_baseline_then_unchanged(self):
        self.assertEqual([f.kind for f in self.run_check(page())], ["baseline"])
        self.assertEqual(self.run_check(page()), [])

    def test_boilerplate_change_is_ignored(self):
        self.run_check(page())
        self.assertEqual(self.run_check(page(boiler="v2 totally different")), [])

    def test_price_change_only(self):
        self.run_check(page(price="490 EUR"))
        f = self.run_check(page(price="590 EUR"))
        self.assertEqual([x.kind for x in f], ["price"])
        self.assertEqual(f[0].detail, "490 \u2192 590 EUR")

    def test_price_format_change_same_amount_is_no_price_finding(self):
        self.run_check(page(price="490 EUR"))
        kinds = [x.kind for x in self.run_check(page(price="490,00 EUR"))]
        self.assertNotIn("price", kinds)

    def test_description_change_only(self):
        self.run_check(page())
        f = self.run_check(page(extra=" Neu: sie ist jetzt kastriert."))
        self.assertEqual([x.kind for x in f], ["description"])

    def test_both_change(self):
        self.run_check(page())
        f = self.run_check(page(price="590 EUR", extra=" Neu: kastriert."))
        self.assertEqual(sorted(x.kind for x in f), ["description", "price"])

    def test_change_is_reported_once(self):
        self.run_check(page())
        self.assertTrue(self.run_check(page(price="590 EUR")))
        self.assertEqual(self.run_check(page(price="590 EUR")), [])


class Layouts(unittest.TestCase):
    def test_label_and_amount_in_separate_paragraphs(self):
        a = '<div id="page-content"><p>Schutzgebühr:</p><p>490 EUR</p><p>Text.</p></div>'
        b = '<div id="page-content"><p>Schutzgebühr:</p><p>590 EUR</p><p>Text.</p></div>'
        store = Store()
        check_description(DOG, parse_page(a), store)
        f = check_description(DOG, parse_page(b), store)
        self.assertEqual([(x.kind, x.detail) for x in f], [("price", "490 \u2192 590 EUR")])

    def test_price_removed_and_added(self):
        with_price = '<div id="page-content"><p>Schutzgebühr: 490 EUR</p><p>Text.</p></div>'
        without = '<div id="page-content"><p>Text.</p></div>'
        store = Store()
        check_description(DOG, parse_page(with_price), store)
        f = check_description(DOG, parse_page(without), store)
        self.assertEqual([(x.kind, x.detail) for x in f], [("price", "490 EUR \u2192 kein Preis")])
        f = check_description(DOG, parse_page(with_price), store)
        self.assertEqual([(x.kind, x.detail) for x in f], [("price", "kein Preis \u2192 490 EUR")])

    def test_inline_markup_keeps_price_on_one_line(self):
        html = ('<div id="page-content"><p><strong>Schutzgebühr:</strong> <span>490</span> EUR'
                '<br>Zweite Zeile</p></div>')
        self.assertIn("Schutzgebühr: 490 EUR", parse_page(html).description.splitlines())


class Runner(unittest.TestCase):
    def test_run_collects_findings_and_errors(self):
        pages = {"https://x.test/nera/": page(), "https://x.test/bad/": "<html></html>"}
        store = Store()
        dogs = [DOG, DogRef(key="H/bad", name="bad", url="https://x.test/bad/")]
        r1 = run(dogs, store, fetch=lambda u: pages[u])
        self.assertEqual((r1.checked, r1.baselined, len(r1.findings), len(r1.errors)), (1, 1, 0, 1))
        pages["https://x.test/nera/"] = page(price="790,00 EUR")
        seen = []
        r2 = run(dogs, store, fetch=lambda u: pages[u], on_progress=lambda d, t: seen.append((d, t)))
        self.assertEqual([(f.kind, f.detail) for f in r2.findings], [("price", "490 \u2192 790 EUR")])
        self.assertEqual(seen, [(1, 2), (2, 2)])


if __name__ == "__main__":
    unittest.main()

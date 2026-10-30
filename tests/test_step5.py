import os
import tempfile
import unittest
from types import SimpleNamespace

from dogwatch import DogRef, Finding
from source.dogwatch_adapter import (CHANGED_SECTION, DB_NAME, build_dog_refs,
                                     parse_changed_entries, reason_for, run_dogwatch,
                                     write_changed_section)

REIST_BALD = {"reist bald"}


def plan(gender, pets=None, error=None):
    doglist = None if error else SimpleNamespace(pets=pets or [])
    return SimpleNamespace(gender=gender, error=error, doglist=doglist)


def pet(name, spec="", url=None):
    return {"name": name, "spec": spec, "url": url or f"https://x.test/{name}/"}


class BuildRefs(unittest.TestCase):
    def test_refs_skip_errors_and_reist_bald_and_mark_missing_folders(self):
        with tempfile.TemporaryDirectory() as dogs:
            os.makedirs(os.path.join(dogs, "Rüden", "benny"))
            plans = [plan("Rüden", [pet("benny"), pet("timosha", "reist bald"), pet("neu")]),
                     plan("Hündinen", error="boom")]
            pairs = build_dog_refs(plans, dogs, REIST_BALD)
        self.assertEqual([(g, r.key, bool(r.folder)) for g, r in pairs],
                         [("Rüden", "Rüden/benny", True), ("Rüden", "Rüden/neu", False)])
        self.assertTrue(pairs[0][1].folder.endswith("benny"))


class Reasons(unittest.TestCase):
    def test_reason_texts(self):
        dog = DogRef("k", "n", "u")
        self.assertEqual(reason_for(Finding(dog, "price", "490 \u2192 590 EUR")),
                         "Schutzgebühr 490 \u2192 590 EUR")
        self.assertEqual(reason_for(Finding(dog, "description", "+1 / -1 Zeilen")),
                         "Beschreibung geändert (+1 / -1 Zeilen)")
        self.assertEqual(reason_for(Finding(dog, "photo_count", "5 online / 4 lokal")),
                         "Fotozahl 5 online / 4 lokal")
        self.assertEqual(reason_for(Finding(dog, "first_photo", "1. Foto geändert")),
                         "1. Foto geändert")


class ReportSection(unittest.TestCase):
    def test_new_file_roundtrip_and_umlauts(self):
        with tempfile.TemporaryDirectory() as rp:
            write_changed_section(rp, "Rüden", {"bärchen": ["Schutzgebühr 490 \u2192 590 EUR", "1. Foto geändert"]})
            text = open(os.path.join(rp, "Rüden_report.txt"), encoding="utf-8").read()
        self.assertEqual(parse_changed_entries(text),
                         [("bärchen", "Schutzgebühr 490 \u2192 590 EUR; 1. Foto geändert")])

    def test_existing_report_is_kept_and_section_is_replaced_not_duplicated(self):
        with tempfile.TemporaryDirectory() as rp:
            path = os.path.join(rp, "Rüden_report.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("Report created: 2026-10-30 10:00:00\n====\n\nGEBLIEBEN:\n    * benny\n\nNEUE:\n    * neu\n")
            write_changed_section(rp, "Rüden", {"benny": ["Beschreibung geändert (+1 / -0 Zeilen)"]})
            write_changed_section(rp, "Rüden", {"neu": ["Fotozahl 2 online / 1 lokal"]})
            text = open(path, encoding="utf-8").read()
        self.assertEqual(text.count(CHANGED_SECTION), 1)
        self.assertIn("GEBLIEBEN:\n    * benny", text)
        self.assertIn("NEUE:\n    * neu", text)
        self.assertEqual(parse_changed_entries(text), [("neu", "Fotozahl 2 online / 1 lokal")])

    def test_empty_section(self):
        with tempfile.TemporaryDirectory() as rp:
            write_changed_section(rp, "Rüden", {})
            text = open(os.path.join(rp, "Rüden_report.txt"), encoding="utf-8").read()
        self.assertIn(CHANGED_SECTION, text)
        self.assertEqual(parse_changed_entries(text), [])

    def test_other_sections_still_parse_like_before(self):
        # same logic as gui.parse_report_section: the new section must not break it
        def parse(text, section):
            out, inside = [], False
            for line in text.splitlines():
                if line.strip().upper() == section:
                    inside = True
                    continue
                if inside:
                    if line.strip() == "" or line.strip().endswith(":"):
                        break
                    if line.strip().startswith("*"):
                        out.append(line.strip().lstrip("*").strip())
            return out
        with tempfile.TemporaryDirectory() as rp:
            path = os.path.join(rp, "g_report.txt")
            open(path, "w", encoding="utf-8").write("GEBLIEBEN:\n    * a\n    * b\n\nNEUE:\n    * c\n")
            write_changed_section(rp, "g", {"a": ["x"]})
            text = open(path, encoding="utf-8").read()
        self.assertEqual(parse(text, "GEBLIEBEN:"), ["a", "b"])
        self.assertEqual(parse(text, "NEUE:"), ["c"])
        self.assertEqual(parse(text, CHANGED_SECTION), ["a"])


def html(name, price, photos, extra=""):
    links = "".join(f'<div class="img-box-shadow"><a href="https://x.test/{name}/p{k}.jpg"></a></div>'
                    for k in range(1, photos + 1))
    return (f'<div id="page-content"><p>Schutzgebühr: {price} EUR</p><p>Lieb.{extra}</p>'
            f'<div class="gal-container">{links}</div>'
            f'<p>Sie wird nach positiver Vorkontrolle vermittelt.</p></div>')


class EndToEnd(unittest.TestCase):
    def test_two_runs_with_fake_network(self):
        with tempfile.TemporaryDirectory() as root:
            dogs_path, report_path = os.path.join(root, "dogs"), os.path.join(root, "reports")
            for name in ("benny", "luna"):
                d = os.path.join(dogs_path, "Rüden", name)
                os.makedirs(d)
                for k in (1, 2):
                    open(os.path.join(d, f"{name}{k}.jpg"), "wb").write(f"{name}-{k}".encode())
            plans = [plan("Rüden", [pet("benny"), pet("luna"), pet("timosha", "reist bald")]),
                     plan("Hündinen", error="offline")]
            pages = {"https://x.test/benny/": html("benny", 490, 2), "https://x.test/luna/": html("luna", 490, 2)}
            fetched = []

            def fetch(url):
                fetched.append(url)
                return pages[url]

            def head_size(url):          # every site photo has the size of the local file
                name = url.split("/")[-2]
                k = url.rsplit("p", 1)[-1].split(".")[0]
                return len(f"{name}-{k}".encode())

            kw = dict(dogs_path=dogs_path, report_path=report_path, reist_bald=REIST_BALD,
                      fetch=fetch, head_size=head_size, get_bytes=lambda u: b"x")
            seen = []
            s1 = run_dogwatch(plans, on_progress=lambda d, t: seen.append((d, t)), **kw)
            self.assertEqual((s1.n_changed, s1.baselined, s1.checked, s1.errors), (0, 2, 2, []))
            self.assertEqual(seen[-1], (2, 2))
            self.assertNotIn("https://x.test/timosha/", fetched)          # reist bald not fetched
            self.assertTrue(os.path.isfile(os.path.join(report_path, DB_NAME)))
            self.assertFalse(os.path.exists(os.path.join(report_path, "Hündinen_report.txt")))

            pages["https://x.test/benny/"] = html("benny", 590, 2)                    # price up
            os.remove(os.path.join(dogs_path, "Rüden", "luna", "luna2.jpg"))  # a photo is gone
            s2 = run_dogwatch(plans, **kw)
            self.assertEqual(s2.n_changed, 2)
            self.assertEqual(s2.changed["Rüden"], {
                "benny": ["Schutzgebühr 490 \u2192 590 EUR"],
                "luna": ["Fotozahl 2 online / 1 lokal"]})
            text = open(os.path.join(report_path, "Rüden_report.txt"), encoding="utf-8").read()
            self.assertEqual(parse_changed_entries(text), [
                ("benny", "Schutzgebühr 490 \u2192 590 EUR"),
                ("luna", "Fotozahl 2 online / 1 lokal")])

            s3 = run_dogwatch(plans, **kw)                                    # nothing new now
            self.assertEqual(s3.changed["Rüden"].get("benny"), None)           # price already reported
            self.assertEqual(list(s3.changed["Rüden"]), ["luna"])              # photo problem persists

    def test_dead_page_is_reported_as_error_not_crash(self):
        with tempfile.TemporaryDirectory() as root:
            plans = [plan("Rüden", [pet("benny")])]
            def fetch(url):
                raise IOError("down")
            s = run_dogwatch(plans, dogs_path=root, report_path=os.path.join(root, "r"),
                             reist_bald=REIST_BALD, fetch=fetch)
            self.assertEqual((s.checked, len(s.errors), s.n_changed), (0, 1, 0))


if __name__ == "__main__":
    unittest.main()

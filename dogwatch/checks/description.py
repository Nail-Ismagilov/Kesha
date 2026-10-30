"""Description check, including the price (Schutzgebühr) flag.

The price is part of the description text, so one hash covers both. When the
hash changed, the old and new text are compared: a changed Schutzgebühr gives
a "price" finding (old -> new), any other wording change a "description" one.
"""
import difflib
import hashlib
import re
import unicodedata

from ..models import Finding
from ..page import PRICE_RE


def normalize(text):
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", " ", text).strip().lower()


def text_hash(text):
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def parse_price(text):
    """First Schutzgebühr amount in `text` as a float (EUR), or None."""
    m = PRICE_RE.search(text or "")
    if not m:
        return None
    return float(m.group(1).replace(".", "").replace(",", "."))


def _fmt(price):
    return f"{price:.0f}" if price == int(price) else f"{price:.2f}"


def _price_detail(old, new):
    if old is not None and new is not None:
        return f"{_fmt(old)} \u2192 {_fmt(new)} EUR"
    if new is None:
        return f"{_fmt(old)} EUR \u2192 kein Preis"
    return f"kein Preis \u2192 {_fmt(new)} EUR"


def _without_price(text):
    """Text with the Schutzgebühr label+amount removed (works for any line layout)."""
    return PRICE_RE.sub("", text)


def _summary(old, new):
    diff = list(difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=0))
    added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
    removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
    return f"+{added} / -{removed} Zeilen"


def check_description(dog, page, store):
    new_text = page.description
    new_hash = text_hash(new_text)
    old = store.get_description(dog.key)

    if old is None:
        store.put_description(dog.key, new_hash, new_text, changed=False)
        return [Finding(dog, "baseline")]

    old_hash, old_text = old
    if old_hash == new_hash:
        store.put_description(dog.key, new_hash, new_text, changed=False)
        return []

    findings = []
    old_price, new_price = parse_price(old_text), parse_price(new_text)
    if old_price != new_price:
        findings.append(Finding(dog, "price", _price_detail(old_price, new_price)))
    old_rest, new_rest = _without_price(old_text), _without_price(new_text)
    if normalize(old_rest) != normalize(new_rest) or not findings:
        findings.append(Finding(dog, "description", _summary(old_rest, new_rest)))
    store.put_description(dog.key, new_hash, new_text, changed=True)
    return findings

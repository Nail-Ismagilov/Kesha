"""Detect changed descriptions / photos of dogs that already exist locally.

A small ``fingerprint.json`` is stored inside each dog's folder. It has two
independent sections, each with its own baseline and ``checked_at``:

* ``description`` - SHA-256 of the normalized scraped text (title/template are
                     NOT part of it, they contain random words) plus the text
                     itself so a diff can be produced.
* ``images``      - SHA-256 + perceptual hash (+ ETag / size) per photo.
                     Photos are matched by content, so re-encoding,
                     re-ordering or a new CDN URL for the same picture is not
                     reported as a change.

A missing section only rebuilds that section. The first run for a section
silently writes a baseline (no false alarms). Files written by the first
version (flat layout) are upgraded transparently.
"""
import difflib
import hashlib
import io
import json
import os
import re
import unicodedata
from datetime import datetime

import imagehash
from PIL import Image

from source.elements_from_url import SESSION, DEFAULT_TIMEOUT, fetch_soup

FP_FILE = "fingerprint.json"
FP_VERSION = 2
PHASH_THRESHOLD = 8  # max Hamming distance for "same picture"
SPLIT_MARKER = "wird nach positiver Vorkontrolle "


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _norm(text):
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", " ", text).strip().lower()


def text_hash(text):
    return hashlib.sha256(_norm(text).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #
def _fp_path(dog_path):
    return os.path.join(dog_path, FP_FILE)


def _upgrade(fp):
    """Return a v2 dict {'version', 'description', 'images'}; a section is None
    when it has no baseline yet. Accepts None and the old flat v1 layout."""
    if not fp:
        return {"version": FP_VERSION, "description": None, "images": None}
    if fp.get("version") == FP_VERSION:
        return {"version": FP_VERSION,
                "description": fp.get("description"),
                "images": fp.get("images")}
    text = fp.get("description") or ""
    return {
        "version": FP_VERSION,
        "description": {"text": text,
                        "hash": fp.get("description_hash") or text_hash(text)},
        "images": {"items": fp.get("images") or []},
    }


def load_fp(dog_path):
    try:
        with open(_fp_path(dog_path), "r", encoding="utf-8") as f:
            return _upgrade(json.load(f))
    except (FileNotFoundError, ValueError, OSError):
        return _upgrade(None)


def save_fp(dog_path, fp):
    """Atomic write (temp file + replace) so OneDrive never syncs a half file."""
    path = _fp_path(dog_path)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(fp, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Photos
# --------------------------------------------------------------------------- #
def _image_entry(url, data, etag, size):
    img = Image.open(io.BytesIO(data)).convert("RGB")
    return {
        "url": url,
        "sha256": hashlib.sha256(data).hexdigest(),
        "phash": str(imagehash.phash(img)),
        "etag": etag,
        "size": size,
    }


def _head_info(url):
    try:
        r = SESSION.head(url, allow_redirects=True, timeout=DEFAULT_TIMEOUT)
        return r.headers.get("ETag"), r.headers.get("Content-Length")
    except Exception:
        return None, None


def _fingerprint_images(urls, old_images):
    """Fingerprint every gallery image, re-downloading only when the URL is new
    or ETag / Content-Length differ from the stored fingerprint."""
    old_by_url = {i["url"]: i for i in old_images}
    result = []
    for url in urls:
        etag, size = _head_info(url)
        old = old_by_url.get(url)
        if old and ((etag and etag == old.get("etag"))
                    or (not etag and size and size == old.get("size"))):
            result.append(old)
            continue
        try:
            resp = SESSION.get(url, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            if not resp.headers.get("Content-Type", "").startswith("image/"):
                raise ValueError("not an image response")
            result.append(_image_entry(url, resp.content, etag, size))
        except Exception as e:
            print(f"[WARN] Could not fingerprint image {url}: {e}")
            if old:  # keep the previous state rather than report a bogus change
                result.append(old)
    return result


def _same_image(a, b):
    if a["sha256"] == b["sha256"]:
        return True
    return (imagehash.hex_to_hash(a["phash"])
            - imagehash.hex_to_hash(b["phash"])) <= PHASH_THRESHOLD


def _diff_images(old_items, new_items):
    """Return (added_urls, removed_urls), matching photos by content."""
    left = list(old_items)
    added = []
    for n in new_items:
        hit = next((o for o in left if _same_image(o, n)), None)
        if hit is not None:
            left.remove(hit)
        else:
            added.append(n["url"])
    return added, [o["url"] for o in left]


# --------------------------------------------------------------------------- #
# Independent section checks: (new_section, status, change)
# status is 'baseline' | 'same' | 'changed'
# --------------------------------------------------------------------------- #
def _check_description(old, description):
    new = {"text": description, "hash": text_hash(description), "checked_at": _now()}
    if old is None:
        return new, "baseline", None
    if old["hash"] == new["hash"]:
        return old, "same", None
    diff = "\n".join(difflib.unified_diff(
        old.get("text", "").splitlines(), description.splitlines(),
        "vorher", "nachher", lineterm=""))
    return new, "changed", diff


def _check_images(old, urls):
    old_items = old["items"] if old else []
    if old_items and not urls:
        # Gallery vanished entirely: more likely a page glitch than a real
        # change. Keep the old photo state.
        return old, "same", None
    new = {"items": _fingerprint_images(urls, old_items), "checked_at": _now()}
    if old is None:
        return new, "baseline", None
    added, removed = _diff_images(old_items, new["items"])
    if added or removed:
        return new, "changed", {"added": added, "removed": removed}
    return old, "same", None


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def check_dog_changes(dog, dry_run=False, check_images=True):
    """Check one already-existing Dog against its stored fingerprint.

    Returns:
      {}                       nothing changed
      {"baseline": True}       nothing changed, but a section had no baseline yet
      {"description": diff,    real changes; keys are present per changed part
       "images": {"added": [...], "removed": [...]}}

    The description and the photos are compared independently and stored in
    separate sections; with check_images=False only the (cheap) text check runs
    and the photo section is left untouched. Only fingerprint.json is ever
    written; the dog's description file and photos are never touched. With
    dry_run=True nothing at all is written, so the GUI preview stays read-only.
    """
    soup = fetch_soup(dog.url)
    try:
        if soup.find("div", attrs={"id": "page-content"}) is None:
            raise ValueError("detail page has no #page-content")
        # Gallery URLs MUST be read before get_description(), which rewrites
        # every <a> inside #page-content (the gallery lives in the same div).
        urls = []
        gallery = soup.find("div", attrs={"class": "gal-container"})
        if gallery is not None:
            for box in gallery.findAll("div", attrs={"class": "img-box-shadow"}):
                if box.a is not None and box.a.get("href"):
                    urls.append(box.a["href"])
        description = dog.get_description(soup).split(SPLIT_MARKER)[0].strip()
    finally:
        soup.decompose()

    path = dog.get_path()
    fp = load_fp(path)

    desc_sec, d_status, d_change = _check_description(fp["description"], description)
    if check_images:
        img_sec, i_status, i_change = _check_images(fp["images"], urls)
    else:
        img_sec, i_status, i_change = fp["images"], "skipped", None

    dirty = d_status in ("baseline", "changed") or i_status in ("baseline", "changed")
    if dirty and not dry_run:
        save_fp(path, {"version": FP_VERSION, "description": desc_sec, "images": img_sec})

    changes = {}
    if d_status == "changed":
        changes["description"] = d_change
    if i_status == "changed":
        changes["images"] = i_change
    if changes:
        return changes
    if "baseline" in (d_status, i_status):
        return {"baseline": True}
    return {}


def find_changed_dogs(gender, pets, log=None, check_images=True):
    """Read-only scan of one category for the GUI preview.

    `pets` is the raw listing already scraped by Doglist. Only dogs that exist
    locally are checked (new dogs have nothing to compare against). Returns
    ({dog_name: changes}, number_of_dogs_without_baseline). One failing dog
    never aborts the scan; it is reported through `log` and skipped.
    """
    # Imported lazily to avoid import cycles with manage_folder / dogs.
    from source.dogs import Dog
    from source.dogs_from_url import REIST_BALD

    changed = {}
    baseline = 0
    for pet in pets:
        if pet["spec"] in REIST_BALD:
            continue
        dog = Dog(pet, gender)
        if not dog.dog_exist():
            continue
        try:
            changes = check_dog_changes(dog, dry_run=True, check_images=check_images)
        except Exception as e:
            if log:
                log(f"  ⚠ {dog.name}: Änderungsprüfung fehlgeschlagen ({e})\n")
            continue
        if "baseline" in changes:
            baseline += 1
        elif changes:
            changed[dog.name] = changes
    return changed, baseline

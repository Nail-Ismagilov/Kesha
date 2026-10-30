"""Detect changes of dogs that already exist locally.

Three independent checks per dog, all based on the dog's detail page:

* description  - SHA-256 of the normalized scraped text (title/template are NOT
                 part of it, they contain random words), stored in a small
                 ``fingerprint.json`` inside the dog's folder. The first run
                 silently writes a baseline (no false alarm).
* first photo  - the first gallery photo on the website is compared with the
                 first photo saved locally (``<name>1.jpg``). Cheap path: if
                 the website file has the same size (HEAD request) as the local
                 file it is treated as unchanged; otherwise the photo is
                 downloaded and compared by SHA-256, falling back to a
                 perceptual hash so a re-encoded copy of the same picture is
                 not reported.
* photo count  - number of gallery photos on the website vs. number of image
                 files in the dog's folder.

No per-photo fingerprints are stored; photos are compared against the files
that are already in the dog's folder.
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
FP_VERSION = 3
PHASH_THRESHOLD = 8  # max Hamming distance for "same picture"
SPLIT_MARKER = "wird nach positiver Vorkontrolle "
PHOTO_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _norm(text):
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", " ", text).strip().lower()


def text_hash(text):
    return hashlib.sha256(_norm(text).encode("utf-8")).hexdigest()


def count_local_photos(dog_path):
    """Number of image files in a dog's folder."""
    try:
        return sum(1 for n in os.listdir(dog_path) if n.lower().endswith(PHOTO_EXTS))
    except OSError:
        return 0


# --------------------------------------------------------------------------- #
# Description fingerprint storage
# --------------------------------------------------------------------------- #
def _fp_path(dog_path):
    return os.path.join(dog_path, FP_FILE)


def _upgrade(fp):
    """Return {'version', 'description'}; description is None without baseline.
    Accepts None, the flat v1 layout and v2 files (their image data is dropped)."""
    if not fp:
        return {"version": FP_VERSION, "description": None}
    if fp.get("version") in (2, FP_VERSION):
        return {"version": FP_VERSION, "description": fp.get("description")}
    text = fp.get("description") or ""
    return {
        "version": FP_VERSION,
        "description": {"text": text,
                        "hash": fp.get("description_hash") or text_hash(text)},
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


def _check_description(old, description):
    """Return (new_section, status, diff); status is baseline | same | changed."""
    new = {"text": description, "hash": text_hash(description), "checked_at": _now()}
    if old is None:
        return new, "baseline", None
    if old["hash"] == new["hash"]:
        return old, "same", None
    diff = "\n".join(difflib.unified_diff(
        old.get("text", "").splitlines(), description.splitlines(),
        "vorher", "nachher", lineterm=""))
    return new, "changed", diff


# --------------------------------------------------------------------------- #
# First photo
# --------------------------------------------------------------------------- #
def _head_size(url):
    try:
        r = SESSION.head(url, allow_redirects=True, timeout=DEFAULT_TIMEOUT)
        return r.headers.get("Content-Length")
    except Exception:
        return None


def _same_picture(local_bytes, site_bytes):
    if hashlib.sha256(local_bytes).digest() == hashlib.sha256(site_bytes).digest():
        return True
    try:
        a = imagehash.phash(Image.open(io.BytesIO(local_bytes)).convert("RGB"))
        b = imagehash.phash(Image.open(io.BytesIO(site_bytes)).convert("RGB"))
        return (a - b) <= PHASH_THRESHOLD
    except Exception:
        return False


def _first_photo_status(dog, urls, path):
    """None (unchanged / unknown), 'changed' or 'missing' (no local first photo)."""
    if not urls:
        return None
    local_first = os.path.join(path, f"{dog.name}1.jpg")
    if not os.path.isfile(local_first):
        return "missing"
    url = urls[0]
    size = _head_size(url)
    if size is not None and str(size) == str(os.path.getsize(local_first)):
        return None  # same size -> assume unchanged, no download
    try:
        resp = SESSION.get(url, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        if not resp.headers.get("Content-Type", "").startswith("image/"):
            raise ValueError("not an image response")
        site_bytes = resp.content
    except Exception as e:
        print(f"[WARN] Could not fetch first photo of {dog.name}: {e}")
        return None  # unknown -> do not raise a false alarm
    with open(local_first, "rb") as f:
        local_bytes = f.read()
    return None if _same_picture(local_bytes, site_bytes) else "changed"


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def check_dog_changes(dog, dry_run=False):
    """Check one already-existing Dog.

    Returns a dict; the keys that are present say what is different:
      "description": unified diff of the old/new description
      "first_photo": "changed" | "missing"
      "photo_count": (photos on the website, image files locally)
    If nothing is different it returns {} - or {"baseline": True} when only the
    description baseline had to be created.

    Only fingerprint.json (description) is ever written; the dog's description
    file and photos are never touched. With dry_run=True nothing is written.
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
    changes = {}

    fp = load_fp(path)
    desc_sec, d_status, d_change = _check_description(fp["description"], description)
    if d_status in ("baseline", "changed") and not dry_run:
        save_fp(path, {"version": FP_VERSION, "description": desc_sec})
    if d_status == "changed":
        changes["description"] = d_change

    first = _first_photo_status(dog, urls, path)
    if first:
        changes["first_photo"] = first

    local_count = count_local_photos(path)
    if len(urls) != local_count:
        changes["photo_count"] = (len(urls), local_count)

    if changes:
        return changes
    return {"baseline": True} if d_status == "baseline" else {}


def existing_dogs(gender, pets):
    """Dogs from the scraped listing `pets` that currently have a local folder
    ("reist bald" entries excluded). Cheap: only filesystem checks."""
    # Imported lazily to avoid import cycles with manage_folder / dogs.
    from source.dogs import Dog
    from source.dogs_from_url import REIST_BALD

    dogs = []
    for pet in pets:
        if pet["spec"] in REIST_BALD:
            continue
        dog = Dog(pet, gender)
        if dog.dog_exist():
            dogs.append(dog)
    return dogs


def check_dogs(dogs, dry_run=True, log=None, on_dog_done=None):
    """Run check_dog_changes over `dogs`. Returns ({dog_name: changes},
    number_of_dogs_without_baseline). One failing dog never aborts the run; it
    is reported through `log` and skipped. `on_dog_done` fires once per dog
    (also on failure) so callers can drive a progress bar."""
    changed = {}
    baseline = 0
    for dog in dogs:
        changes = None
        try:
            changes = check_dog_changes(dog, dry_run=dry_run)
        except Exception as e:
            if log:
                log(f"  ⚠ {dog.name}: Änderungsprüfung fehlgeschlagen ({e})\n")
        if changes is not None:
            if "baseline" in changes:
                baseline += 1
            elif changes:
                changed[dog.name] = changes
        if on_dog_done:
            on_dog_done()
    return changed, baseline

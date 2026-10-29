"""Detect changed descriptions / photos of dogs that already exist locally.

A small ``fingerprint.json`` is stored inside each dog's folder. On every run
the current shelter page is compared against it:

* description  - SHA-256 of the normalized scraped text (title/template are
                 NOT part of it, they contain random words)
* photos       - SHA-256 + perceptual hash per image. Images are matched by
                 content, so re-encoding, re-ordering or a new CDN URL for the
                 same picture is not reported as a change.

The first run for a dog silently writes a baseline (no false alarms).
"""
import difflib
import hashlib
import io
import json
import os
import re
import unicodedata

import imagehash
from PIL import Image

from source.elements_from_url import SESSION, DEFAULT_TIMEOUT, fetch_soup

FP_FILE = "fingerprint.json"
PHASH_THRESHOLD = 8  # max Hamming distance for "same picture"
SPLIT_MARKER = "wird nach positiver Vorkontrolle "


def _norm(text):
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", " ", text).strip().lower()


def text_hash(text):
    return hashlib.sha256(_norm(text).encode("utf-8")).hexdigest()


def _fp_path(dog_path):
    return os.path.join(dog_path, FP_FILE)


def load_fp(dog_path):
    try:
        with open(_fp_path(dog_path), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError, OSError):
        return None


def save_fp(dog_path, fp):
    """Atomic write (temp file + replace) so OneDrive never syncs a half file."""
    path = _fp_path(dog_path)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(fp, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


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


def compare(old, new):
    """Return {} if nothing changed, else keys 'description' (unified diff)
    and/or 'images' ({'added': [urls], 'removed': [urls]})."""
    changes = {}
    if old["description_hash"] != new["description_hash"]:
        changes["description"] = "\n".join(difflib.unified_diff(
            old["description"].splitlines(), new["description"].splitlines(),
            "vorher", "nachher", lineterm=""))
    left = list(old["images"])
    added = []
    for n in new["images"]:
        hit = next((o for o in left if _same_image(o, n)), None)
        if hit is not None:
            left.remove(hit)
        else:
            added.append(n["url"])
    if added or left:
        changes["images"] = {"added": added, "removed": [o["url"] for o in left]}
    return changes


def check_dog_changes(dog):
    """Check one already-existing Dog against its stored fingerprint.

    Returns {} (unchanged), {"baseline": True} (first run, fingerprint written)
    or a dict as described in compare(). Only fingerprint.json is written;
    the dog's description file and photos are never touched.
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
    old = load_fp(path)
    old_images = old["images"] if old else []
    if old_images and not urls:
        # Gallery vanished entirely: more likely a page glitch than a real
        # change. Keep the old photo state, still check the description.
        images = old_images
    else:
        images = _fingerprint_images(urls, old_images)

    new = {
        "description": description,
        "description_hash": text_hash(description),
        "images": images,
    }
    if old is None:
        save_fp(path, new)
        return {"baseline": True}
    changes = compare(old, new)
    if changes:
        save_fp(path, new)
    return changes

"""Photo-count check.

Number of gallery photos on the website vs. number of photo files of this dog in
its folder (<name>1.jpg, <name>2.jpg, ...). Other files in the folder (the ad
text, fingerprints, pictures you added yourself) are not counted.
"""
import os
import re

from ..models import Finding

_EXT = r"(?:jpe?g|png|webp|gif)"


def count_local_photos(folder, name):
    try:
        names = os.listdir(folder)
    except OSError:
        return 0
    rx = re.compile(rf"^{re.escape(name)}\d+\.{_EXT}$", re.IGNORECASE)
    return sum(1 for n in names if rx.match(n))


def check_photo_count(dog, page, ctx):
    if not dog.folder:
        return []
    site = len(page.photo_urls)
    local = count_local_photos(dog.folder, dog.name)
    if site == local:
        return []
    hint = " (Galerie auf der Seite leer?)" if site == 0 else ""
    return [Finding(dog, "photo_count", f"{site} online / {local} lokal{hint}")]

"""First-photo check.

The first gallery photo on the website is compared with the first photo that is
already stored in the dog's folder (<folder>/<name>1.jpg). Nothing is stored in
the database: the local file is the reference.

Cheap path: if the website file has the same size (one HEAD request) as the
local file, it is treated as unchanged and nothing is downloaded. Only if the
size differs (or is unknown) the photo is downloaded and compared.
"""
import os

from ..imagecmp import same_picture
from ..models import Finding


def check_first_photo(dog, page, ctx):
    if not dog.folder or not page.photo_urls:
        return []          # nothing to compare (photo count is a separate check)

    local_path = os.path.join(dog.folder, f"{dog.name}1.jpg")
    if not os.path.isfile(local_path):
        return [Finding(dog, "first_photo", "1. Foto fehlt lokal")]

    url = page.photo_urls[0]
    size = ctx.head_size(url)
    if size is not None and size == os.path.getsize(local_path):
        return []

    try:
        site_bytes = ctx.get_bytes(url)
    except Exception as e:
        return [Finding(dog, "warning", f"1. Foto nicht ladbar: {e}")]

    with open(local_path, "rb") as f:
        local_bytes = f.read()
    if same_picture(local_bytes, site_bytes):
        return []
    return [Finding(dog, "first_photo", "1. Foto geändert")]

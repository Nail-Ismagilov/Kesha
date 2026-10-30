"""Compare two images: identical bytes, or visually the same picture.

The perceptual part (dHash) needs Pillow. Without Pillow only byte-identical
images count as equal.
"""
import hashlib
import io

DHASH_THRESHOLD = 10   # max differing bits of 64 for "same picture"


def dhash(data):
    """64-bit difference hash, or None if Pillow is unavailable / data unreadable."""
    try:
        from PIL import Image
        resample = getattr(Image, "Resampling", Image).LANCZOS
        img = Image.open(io.BytesIO(data)).convert("L").resize((9, 8), resample)
    except Exception:
        return None
    px = list(img.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            i = row * 9 + col
            bits = (bits << 1) | (1 if px[i] > px[i + 1] else 0)
    return bits


def same_picture(a, b):
    if hashlib.sha256(a).digest() == hashlib.sha256(b).digest():
        return True
    ha, hb = dhash(a), dhash(b)
    if ha is None or hb is None:
        return False
    return bin(ha ^ hb).count("1") <= DHASH_THRESHOLD

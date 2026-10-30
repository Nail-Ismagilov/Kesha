"""Parse a dog's detail page ONCE; every check reads the result."""
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

SPLIT_MARKER = "wird nach positiver Vorkontrolle"
PRICE_LABEL = "schutzgeb"          # Schutzgebühr / Schutzgebuehr / Schutzgebür

# "Schutzgebühr: 590 EUR", "Schutzgebühr: 790,00 EUR", "Schutzgebühr 1.200,50 €".
# \s* also spans a line break, so label and amount may sit in different blocks.
PRICE_RE = re.compile(
    r"schutzgeb\w*\s*[:\uff1a]?\s*([0-9][0-9.]*(?:,[0-9]{1,2})?)\s*(?:\u20ac|eur)",
    re.IGNORECASE)

_INLINE_TAGS = ["a", "b", "strong", "i", "em", "u", "span", "font", "small", "big", "mark"]


class PageError(Exception):
    pass


@dataclass
class PageData:
    description: str                       # cleaned text, one line per paragraph
    photo_urls: list = field(default_factory=list)


def _clean_lines(text):
    lines = (re.sub(r"[ \t\u00a0]+", " ", ln).strip() for ln in text.splitlines())
    return [ln for ln in lines if ln]


def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    try:
        content = soup.find("div", attrs={"id": "page-content"})
        if content is None:
            raise PageError("detail page has no #page-content")

        # Gallery first (read-only), then remove it so it cannot pollute the text.
        photo_urls = []
        gallery = soup.find("div", attrs={"class": "gal-container"})
        if gallery is not None:
            for box in gallery.find_all("div", attrs={"class": "img-box-shadow"}):
                if box.a is not None and box.a.get("href"):
                    photo_urls.append(box.a["href"])
            gallery.decompose()

        # Make inline markup invisible so "<strong>Schutzgebühr:</strong> 490 EUR"
        # stays ONE line; only block elements (p, li, h*, div, br) break lines.
        for tag in content.find_all(_INLINE_TAGS):
            tag.unwrap()
        for br in content.find_all("br"):
            br.replace_with("\n")
        if hasattr(content, "smooth"):          # bs4 >= 4.8: merge adjacent strings
            content.smooth()

        lines = _clean_lines(content.get_text("\n"))
        full = "\n".join(lines)

        # Everything from the standard "nach positiver Vorkontrolle" sentence on
        # is boilerplate; cut it so a template edit cannot flag every dog. But
        # never lose the price line if it happens to sit behind the marker.
        cut = full.lower().find(SPLIT_MARKER.lower())
        if cut == -1:
            description = full
        else:
            description = full[:cut].rstrip()
            if PRICE_LABEL not in description.lower():
                m = PRICE_RE.search(full[cut:])
                if m:
                    description += "\n" + re.sub(r"\s+", " ", m.group(0))
        return PageData(description=description, photo_urls=photo_urls)
    finally:
        soup.decompose()

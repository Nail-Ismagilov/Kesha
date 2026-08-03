#!/usr/bin/python
import os
from source.elements_from_url import *
import re
import pathlib
import shutil
import random
from source.global_defines import DOGS_PATH, MAKET_PATH

# Streaming write buffer for image downloads. Larger = fewer write iterations
# (a bit faster); still bounds per-download RAM to this size, not the whole file.
IMAGE_CHUNK_SIZE = 64 * 1024  # 64 KB

PFLEGESTELLE = "*befindet sich auf einer Pflegestelle in Deutschland."
adjectives = {
    'male': [
        'Süßer', 'Schöner', 'Lieber',
        'Tapferer', 'Treuer', 'Fröhlicher', 'Neugieriger', 'Charmanter'
    ],
    'female': [
        'Süße', 'Schöne', 'Liebe',
        'Tapfere', 'Treue', 'Fröhliche', 'Neugierige'
    ]
}

endings = {
    'male': [
        'sucht seine Familie', 'sucht liebevolle Familie', 'sucht liebevolles Zuhause', 'sucht ein neues Zuhause'
    ],
    'female': [
        'sucht ihre Familie', 'sucht liebevolle Familie', 'sucht liebevolles Zuhause', 'sucht ein neues Zuhause'
    ]
}


class Dog:
    """Main class Dog with instance url and gender
    """
    def __init__(self, dog, gender):
        self.url = dog['url']
        self.name = dog['name']
        self.gender = gender
        # self.existedList = existedList

    def create_dog(self):
        """Build the dog's folder (description + images).

        Returns (ok, image_count) so callers can surface real per-dog outcomes
        to the user instead of relying on invisible prints: ok=False means the
        folder could not be built (partial folder removed), image_count == 0
        means the description was saved but the photo gallery was missing.
        """
        path = self.get_path()
        self.create_folder(path)
        try:
            # Fetch and parse the detail page exactly ONCE, then reuse the soup
            # for both the description and the images (was fetched 3x before).
            soup = fetch_soup(self.url)
            try:
                # Images MUST be extracted before the description: get_description
                # mutates every <a> tag inside #page-content (replacing links with
                # "text (url)"), and the image gallery is nested inside that same
                # div. Running description-cleanup first destroys the <a href=...>
                # wrappers around each photo before get_and_save_images can read them.
                images = self.get_and_save_images(soup)
                self.set_description(soup)
            finally:
                soup.decompose()  # release the DOM immediately
            return True, images
        except Exception as e:
            # Never leave a half-built folder: dog_exist() only checks that the
            # folder exists, so a partial one would never be retried. Remove it
            # so the next run re-creates it cleanly, and don't abort the batch.
            print(f"[ERROR] Failed to create {self.name}: {e}; removing partial folder.")
            shutil.rmtree(path, ignore_errors=True)
            return False, 0

    def delete_dog(self):
        path = self.get_path()
        self.del_path(path)

    def get_description(self, soup):
        page_content = soup.find('div', attrs = {'id':'page-content'})
        if page_content is None:
            raise ValueError("detail page has no #page-content")

        # Replace <a> tags with "text (url)" so links aren't silently dropped
        # by get_text().
        for a_tag in page_content.find_all('a'):
            link_text = a_tag.get_text()
            link_url = a_tag.get('href', '')
            a_tag.replace_with(f"{link_text} ({link_url})")

        description = page_content.get_text()
        description = self.clean_empty_lines(description)
        description = re.sub(r'https://www.', r'', description)
        description = re.sub(r'Ausreise', r'\nAusreise', description)
        description = re.sub(r'Vorgeschichte', r'\n\nVorgeschichte', description)
        description = re.sub(r'Charakter', r'\nCharakter', description)
        description = re.sub(r'Adoption', r'\nAdoption', description)
        description = re.sub(r'Hier geht es zum Video', r'\nHier geht es zum Video', description)
        return description

    def clean_empty_lines(self, text):
        """Remove empty lines from text. Works with both strings and lists."""
        if isinstance(text, str):
            lines = text.splitlines()
            cleaned = [line for line in lines if line.strip()]
            return '\n'.join(cleaned)
        elif isinstance(text, list):
            return [line for line in text if line.strip()]
        else:
            raise TypeError("Input must be string or list")

    def detect_sex(self, description):
        """Best-effort sex from the scraped text, falling back to the category.

        Category alone is wrong for Pflegestelle (mixed-sex fosters), which used
        to make every foster dog female ("Süße ... sucht ihre Familie"). Prefer
        an explicit marker in the description; fall back to the category; return
        None only when genuinely unknown so the caller can stay neutral.
        """
        text = (description or "").lower()
        if re.search(r"\brüde\b|\brüden\b|\bmännlich\b", text):
            return "male"
        if re.search(r"\bhündin\b|\bhündinnen\b|\bweiblich\b", text):
            return "female"
        if self.gender in ("Rüden", "Welpen_und_Junghunde"):
            return "male"
        if self.gender in ("Hündinen", "Welpen_Madchen"):
            return "female"
        return None

    def get_title(self, description):
        name = self.extract_name(description)
        sex = self.detect_sex(description)
        if sex is None:
            # Unknown sex (e.g. an undetectable Pflegestelle dog): neutral phrasing
            # beats guessing the wrong grammatical gender.
            return f"{name} sucht ein neues Zuhause\n"
        adj = random.choice(adjectives[sex])
        ending = random.choice(endings[sex])
        return f"{adj} {name} {ending}\n"

    def set_description(self, soup):
        description = self.get_description(soup)  # parse once, reuse below
        title = self.get_title(description)       # title already ends in \n
        text_arr = [title, description.split('wird nach positiver Vorkontrolle ')[0]]
        self.compose_text(text_arr)

    def compose_text(self, text_arr):
        # \bName\b matches the standalone placeholder only, not "Namen" etc.
        # clean_string() strips odd casing/punctuation from scraped/local names
        # before it lands in the generated description text.
        clean_name = self.clean_string(self.name)
        with open(MAKET_PATH, "r", encoding="utf-8") as file:
            for word in file:
                word = re.sub(r"\bName\b", clean_name, word)
                text_arr.append(word)
        with open(os.path.join(self.get_path(), f"{self.name}.txt"), "w+", encoding="utf-8") as composed_text:
            for line in text_arr:
                composed_text.write(line)

    def get_and_save_images(self, soup):
        """Download the detail-page gallery. Returns the number of images found
        (0 when the gallery is missing) so the caller can warn about photo-less
        folders instead of the failure vanishing into stdout."""
        table = soup.find('div', attrs = {'class':'gal-container'})
        if table is None:
            return 0
        counter = 0
        for line in table.findAll('div',attrs={'class':'img-box-shadow'}):
            counter += 1
            self.save_image(line.a['href'], counter)
        return counter

    def save_image(self, image_url, counter):
        try:
            # Stream to disk so a large JPEG never fully resides in RAM
            # (peak stays at IMAGE_CHUNK_SIZE, not the whole file).
            with SESSION.get(image_url, timeout=DEFAULT_TIMEOUT, stream=True) as resp:
                resp.raise_for_status()
                ctype = resp.headers.get('Content-Type', '')
                if not ctype.startswith('image/'):
                    # Don't persist a 404/redirect HTML body as a fake .jpg.
                    print(f"[WARN] Skipping non-image response for {self.name}{counter} ({ctype})")
                    return
                with open(os.path.join(self.get_path(), f"{self.name}{counter}.jpg"), 'wb') as handler:
                    for chunk in resp.iter_content(IMAGE_CHUNK_SIZE):
                        handler.write(chunk)
        except Exception as e:
            print(f"Error saving image {counter} for {self.name}: {e}")

    def create_folder(self, path):
        from source.manage_folder import ensure_folder_exists
        ensure_folder_exists(path)

    def dog_exist(self):
        process = False
        if os.path.exists(self.get_path()):
            process = True
        else:
            process = False
        return process

    def get_path(self):
        return os.path.join(DOGS_PATH, self.gender, self.name)

    def del_path(self, path):
        # Reuse manage_folder's safety-guarded, OneDrive/Windows-retry-aware
        # deletion rather than duplicating that logic here.
        from source.manage_folder import del_path as _del_path
        _del_path(path, self.name)

    def extract_name(self, text):
        # Use regex to find the line that starts with "Name:" and extract the name
        match = re.search(r"Name:\s*(.+)", text)
        if match:
            name = match.group(1).strip()
            # Drop trailing annotations like "Bella (reserviert)" or "Bella | ..."
            # so the generated title reads "Süße Bella sucht ..." not the whole line.
            name = re.split(r"\s*[(|]", name)[0].strip()
            return name or self.name
        # Fall back to the known name so titles never contain the word "None".
        return self.name

    def clean_string(self, text):
        # Keep only alphabetic characters, capitalize first letter.
        letters_only = ''.join([char for char in text if char.isalpha()])
        if letters_only:
            return letters_only[0].upper() + letters_only[1:].lower()
        return ""

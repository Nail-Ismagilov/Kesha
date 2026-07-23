from source.dogs_from_PC import Dogs_from_PC
from source.dogs_from_url import REIST_BALD
from source.elements_from_url import urls, get_pets_from_url

class Doglist:
    def __init__(self, gender):
        self.gender = gender
        self.existingList = Dogs_from_PC().dog_list(gender)
        # Scrape the listing page ONCE and keep the raw pet dicts so
        # create_new_dogs can reuse them instead of re-fetching the page.
        self.pets = get_pets_from_url(urls[gender])
        # Online dogs, excluding "reist bald" (travelling) entries. Lowercased
        # and sorted to match Dogs_from_PC's local-folder names (case can
        # differ between the scraped slug and the on-disk folder name).
        self.internetList = sorted(
            p['name'].lower() for p in self.pets if p['spec'] not in REIST_BALD
        )

        # Compute each diff exactly once with O(1) set membership, preserving
        # original order, and cache the results on the instance.
        existing = set(self.existingList)
        internet = set(self.internetList)
        # Safety guard: if the scrape produced nothing (site down, layout change,
        # empty category), treat it as "unknown" and mark NOTHING as adopted, so
        # a transient failure can never wipe every local folder.
        self._happy = [] if not self.internetList else [d for d in self.existingList if d not in internet]
        self._new = [d for d in self.internetList if d not in existing]
        self._left = [d for d in self.internetList if d in existing]
        print(f"[DEBUG] {gender}: {len(self._new)} new, {len(self._happy)} adopted, {len(self._left)} stayed")

    def happy_dogs(self):
        # In existingList but not online (adopted / gone).
        return self._happy

    def new_dogs(self):
        # Online but not local yet (new).
        return self._new

    def left_dogs(self):
        # In both lists (still available).
        return self._left


# print(existingList.dog_list())
# print(fromUrl.dog_list())

# print(dogList.left_dogs())
# print(dogList.happy_dogs())
# print(dogList.new_dogs())

    

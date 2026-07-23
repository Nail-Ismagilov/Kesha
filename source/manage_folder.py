import os
import shutil
import time

from source.dogs import Dog
from source.global_defines import DOGS_PATH
from source.elements_from_url import urls, get_pets_from_url
from source.dogs_from_url import REIST_BALD

def ensure_folder_exists(path):
    """Create the folder if it does not exist."""
    os.makedirs(path, exist_ok=True)

def create_new_dogs(gender, doggies=None, on_dog_done=None):
    # Reuse the listing already scraped by Doglist when provided, so the page
    # is fetched once per gender instead of twice.
    if doggies is None:
        doggies = get_pets_from_url(urls[gender])
    for dog in doggies:
        # Skip "reist bald" dogs: Doglist excludes them from the online list, so
        # creating folders for them here would cause churn + false "adopted".
        if dog['spec'] in REIST_BALD:
            continue
        doggy = Dog(dog, gender)
        if not doggy.dog_exist():
            print(f"doggy = {doggy.name} does not exist")
            doggy.create_dog()
            # Only a genuinely new download counts as a unit of work - skipped
            # (already-existing) dogs are near-instant and shouldn't inflate
            # the "dogs left to download" total the progress bar is based on.
            if on_dog_done:
                on_dog_done()
        else:
            print(f"doggy = {doggy.name} exists")

def get_path(gender, name):
    path = f"{DOGS_PATH}/{gender}/{name}"
    return path

def _handle_remove_readonly(func, file_path, exc):
    """Error handler for Windows readonly files."""
    try:
        os.chmod(file_path, 0o777)
        func(file_path)
    except Exception as e:
        print(f"  Could not delete: {file_path} - {e}")

def _force_delete_contents(folder_path):
    """Manually delete all contents when rmtree leaves stragglers behind."""
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            try:
                os.chmod(file_path, 0o777)
                os.remove(file_path)
            except Exception:
                print(f"  Could not delete file: {file_path}")
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                os.chmod(dir_path, 0o777)
                os.rmdir(dir_path)
            except Exception:
                print(f"  Could not delete dir: {dir_path}")

def del_path(path, name, max_retries=5):
    """Delete a dog's folder, retrying past Windows/OneDrive file locks.

    Defence-in-depth first: refuse empty names or any path that escapes
    DOGS_PATH, and make a missing folder a no-op instead of a crash that
    would abort the rest of the delete loop.
    """
    target = os.path.abspath(path)
    base = os.path.abspath(DOGS_PATH)
    if not name or not target.startswith(base + os.sep):
        print(f"[WARN] Refusing to delete unsafe path: {target!r}")
        return False
    if not os.path.isdir(target):
        print(f"[WARN] Already gone or not a directory: {target}")
        return False

    for attempt in range(max_retries):
        try:
            shutil.rmtree(target, onerror=_handle_remove_readonly)
            time.sleep(0.5)  # let Windows release file handles

            if os.path.isdir(target):
                # Contents survived rmtree (common on OneDrive) - clean up by hand.
                print("  Folder still exists, trying manual deletion...")
                _force_delete_contents(target)
                time.sleep(0.5)
                try:
                    os.rmdir(target)
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"[WARN] Retry {attempt + 1}/{max_retries} for {name}...")
                        time.sleep(2)
                        continue
                    print(f"[ERROR] Cannot delete folder '{name}': {e}")
                    return False

            print(f"Dog folder deleted: {name}")
            return True

        except PermissionError:
            if attempt < max_retries - 1:
                print(f"[WARN] Permission denied for {name}, retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                print(f"[ERROR] Cannot delete '{name}': access denied after {max_retries} attempts "
                      f"(possible causes: OneDrive sync, file in use, insufficient permissions). Path: {target}")
                return False
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[WARN] Error deleting {name}: {e}, retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                print(f"[ERROR] Unexpected error deleting '{name}': {e}")
                return False

    return False

def delete_folder(gender, name):
    path = get_path(gender, name)
    del_path(path, name)

def delete_dog(gender, dog):
    delete_folder(gender, dog)

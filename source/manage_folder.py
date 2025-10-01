import os
import shutil
import time

from source.dogs import Dog
from source.global_defines import DOGS_PATH
from source.elements_from_url import urls, get_pets_from_url

def ensure_folder_exists(path):
    """Create the folder if it does not exist."""
    os.makedirs(path, exist_ok=True)

def create_new_dogs(gender):
    doggies = get_pets_from_url(urls[gender])
    for dog in doggies:
        doggy = Dog(dog, gender)
        if not doggy.dog_exist():
            print(f"doggy = {doggy.name} does not exist")
            doggy.create_dog()
        else:
            print(f"doggy = {doggy.name} exists")

def get_path(gender, name):
    path = f"{DOGS_PATH}/{gender}/{name}"
    return path

def del_path(path, name, max_retries=5):
    """Delete folder with retry logic for Windows/OneDrive compatibility"""
    # Check both os.path.exists and os.path.isdir for OneDrive compatibility
    path_exists = False
    try:
        path_exists = os.path.exists(path) or os.path.isdir(path)
        if not path_exists:
            # Try to access it anyway - OneDrive might be hiding it
            os.listdir(path)
            path_exists = True
    except FileNotFoundError:
        print(f"Path does not exist: {path}")
        return False
    except Exception:
        pass
    
    if not path_exists:
        print(f"Path does not exist: {path}")
        return False
    
    def handle_remove_readonly(func, file_path, exc):
        """Error handler for Windows readonly files"""
        try:
            os.chmod(file_path, 0o777)
            func(file_path)
        except Exception as e:
            print(f"  Could not delete: {file_path} - {e}")
    
    def force_delete_contents(folder_path):
        """Manually delete all contents"""
        try:
            for root, dirs, files in os.walk(folder_path, topdown=False):
                # Delete files
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    try:
                        os.chmod(file_path, 0o777)
                        os.remove(file_path)
                    except Exception as e:
                        print(f"  Could not delete file: {file_path}")
                
                # Delete subdirectories
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        os.chmod(dir_path, 0o777)
                        os.rmdir(dir_path)
                    except Exception as e:
                        print(f"  Could not delete dir: {dir_path}")
        except Exception as e:
            print(f"  Error walking directory: {e}")
    
    for attempt in range(max_retries):
        try:
            # Try shutil.rmtree with error handler
            shutil.rmtree(path, onerror=handle_remove_readonly)
            
            # Wait for Windows to release handles
            time.sleep(0.5)
            
            # Verify deletion - use multiple checks for OneDrive
            still_exists = False
            try:
                still_exists = os.path.exists(path) or os.path.isdir(path) or len(os.listdir(path)) >= 0
            except:
                # If we can't list it, it's probably gone
                still_exists = False
            
            if still_exists:
                # Folder or contents still exist, try manual deletion
                print(f"  Folder still exists, trying manual deletion...")
                force_delete_contents(path)
                time.sleep(0.5)
                
                # Try to remove the empty folder
                try:
                    os.rmdir(path)
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"⚠ Retry {attempt + 1}/{max_retries} for {name}...")
                        time.sleep(2)
                        continue
                    else:
                        print(f"✗ Cannot delete folder '{name}': {e}")
                        return False
            
            print(f"✓ Dog folder deleted: {name}")
            return True
            
        except PermissionError as e:
            if attempt < max_retries - 1:
                print(f"⚠ Permission denied for {name}, retrying... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                print(f"✗ Cannot delete '{name}': Access denied after {max_retries} attempts")
                print(f"  Possible causes: OneDrive sync, file in use, or insufficient permissions")
                print(f"  Path: {path}")
                return False
                
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠ Error deleting {name}: {e}, retrying... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                print(f"✗ Unexpected error deleting '{name}': {e}")
                return False
    
    return False

def delete_folder(gender, name):
    path = get_path(gender, name)
    del_path(path, name)

def delete_dog(gender, dog):
    delete_folder(gender, dog)
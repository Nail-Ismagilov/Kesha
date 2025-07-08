import os
import shutil

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

def del_path(path, name):
    shutil.rmtree(path)
    print(f"Dog folder deleted: {name}")

def delete_folder(gender, name):
        path = get_path(gender, name)
        del_path(path, name)

def delete_dog(gender, dog):
    delete_folder(gender, dog)
from source.dogs import *
from source.global_defines import DOGS_PATH

def create_new_dogs(gender):
    doggies = get_pets_from_url(urls[gender])
    for dog in doggies:
        doggy = Dog(dog['url'], gender)
        if not doggy.dog_exist():
            doggy.create_dog()

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
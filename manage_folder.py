from dogs import *

def new_dogs():
    for gender in urls.keys():
        for url in urls:
            dog = Dog(url, gender)
            if not dog.dog_exist():
                dog.create_dog()

def get_path(gender, name):
    path = f"{pathlib.Path(__file__).parent.resolve()}/hunde/{gender}/{name}"
    return path

def del_path(path, name):
    shutil.rmtree(path)
    print(f"Dog folder deleted: {name}")

def delete_folder(gender, name):
        path = get_path(gender, name)
        del_path(path, name)

def delete_dog(gender, dog):
    delete_folder(gender, dog)
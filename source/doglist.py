from source.dogs_from_url import Dogs_from_URL
from source.dogs_from_PC import Dogs_from_PC

class Doglist:
    def __init__(self):
        self.existingList = Dogs_from_PC().dog_list() 
        self.internetList = Dogs_from_URL().dog_list()
            # existingList = Dogs_from_PC() 
            # fromUrl = Dogs_from_URL()

    def happy_dogs (self):
        happyDogs = {}
        for dogs in self.existingList.keys():
            happyDogs[dogs] = []
            for dog in self.existingList[dogs]:
                if dog not in self.internetList[dogs]:
                    happyDogs[dogs].append(dog)
        return happyDogs
    
    def new_dogs (self):
        newDogs = {}
        for dogs in self.internetList.keys():
            newDogs[dogs] = []
            for dog in self.internetList[dogs]:
                if dog not in self.existingList[dogs]:
                    newDogs[dogs].append(dog)
        return newDogs
    
    def left_dogs (self):
        leftDogs = {}
        for dogs in self.internetList.keys():
            leftDogs[dogs] = []
            for dog in self.internetList[dogs]:
                if dog in self.existingList[dogs]:
                    leftDogs[dogs].append(dog)
        return leftDogs


# print(existingList.dog_list())
# print(fromUrl.dog_list())

# print(dogList.left_dogs())
# print(dogList.happy_dogs())
# print(dogList.new_dogs())

    

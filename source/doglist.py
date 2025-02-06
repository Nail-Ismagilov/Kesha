from source.dogs_from_url import Dogs_from_URL
from source.dogs_from_PC import Dogs_from_PC

class Doglist:
    def __init__(self, gender):
        print ("creating doglist from PC")
        self.existingList = Dogs_from_PC().dog_list(gender) 
        print ("creating doglist from URL")
        self.internetList = Dogs_from_URL().dog_list(gender)
            # existingList = Dogs_from_PC() 
            # fromUrl = Dogs_from_URL()

    def happy_dogs (self):
        happyDogs = {}
        for dogs in self.existingList:
            happyDogs = []
            for dog in self.existingList:
                if dog not in self.internetList:
                    happyDogs.append(dog)
        return happyDogs
    
    def new_dogs (self):
        newDogs = {}
        for dogs in self.internetList:
            newDogs = []
            for dog in self.internetList:
                if dog not in self.existingList:
                    newDogs.append(dog)
        return newDogs
    
    def left_dogs (self):
        leftDogs = {}
        for dogs in self.internetList:
            leftDogs = []
            for dog in self.internetList:
                if dog in self.existingList:
                    leftDogs.append(dog)
        return leftDogs


# print(existingList.dog_list())
# print(fromUrl.dog_list())

# print(dogList.left_dogs())
# print(dogList.happy_dogs())
# print(dogList.new_dogs())

    

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

    def happy_dogs(self):
        # Dogs that are in existingList but not in internetList (gone)
        return [dog for dog in self.existingList if dog not in self.internetList]
    
    def new_dogs(self):
        # Dogs that are in internetList but not in existingList (new)
        return [dog for dog in self.internetList if dog not in self.existingList]
    
    def left_dogs(self):
        # Dogs that are in both lists (still present)
        return [dog for dog in self.internetList if dog in self.existingList]


# print(existingList.dog_list())
# print(fromUrl.dog_list())

# print(dogList.left_dogs())
# print(dogList.happy_dogs())
# print(dogList.new_dogs())

    

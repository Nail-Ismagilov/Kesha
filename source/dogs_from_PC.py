import os
import pathlib
from source.global_defines import DOGS_PATH


class Dogs_from_PC:
    dogs = {}
    # def __init__():
    #     self.name
    def __get_dogs(self, gender):
        dir_path = f"{DOGS_PATH}/{gender}"
        if not os.path.exists(dir_path):
            return []
        dogs = os.listdir(dir_path)
        dogs = [dog.lower() for dog in dogs]
        dogs.sort()  # Sorts in place
        return dogs

    def __get_hundin(self):
        return self.__get_dogs("Hündinen")
    
    def __get_ruden(self):
        return self.__get_dogs("Rüden")
    
    def __get_welpen_madchen(self):
        return self.__get_dogs("Welpen_Madchen")
    
    def __get_welpen_junghunde(self):
        return self.__get_dogs("Welpen_und_Junghunde")
    
    def __get_welpen_pflegestelle(self):
        return self.__get_dogs("Pflegestelle")

    def dog_list(self, gender):
        if gender == "Hündinen":
            return self.__get_hundin()
        elif gender == "Rüden":
            return self.__get_ruden()
        elif gender == "Welpen_Madchen":
            return self.__get_welpen_madchen()
        elif gender == "Welpen_und_Junghunde":
            return self.__get_welpen_junghunde()
        elif gender == "Pflegestelle":
            return self.__get_welpen_pflegestelle()
        # self.dogs["Hündinen"] = self.__get_hundin()
        # self.dogs["Rüden"] = self.__get_ruden()
        # self.dogs["Welpen_Madchen"] = self.__get_welpen_madchen()
        # self.dogs["Welpen_und_Junghunde"] = self.__get_welpen_junghunde()
        # self.dogs["Pflegestelle"] = self.__get_welpen_pflegestelle()
        # return self.dogs


# create_report()
# create_pandoc()
# read_pandoc_csv()

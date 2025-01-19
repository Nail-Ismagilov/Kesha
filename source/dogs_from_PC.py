import os
import pathlib
from source.global_defines import DOGS_PATH


class Dogs_from_PC:
    dogs = {}
    # def __init__():
    #     self.name
    def __get_dogs(self, gender):
        return os.listdir(f"{DOGS_PATH}/{gender}")

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

    def dog_list(self):
        self.dogs["Hündinen"] = self.__get_hundin()
        self.dogs["Rüden"] = self.__get_ruden()
        self.dogs["Welpen_Madchen"] = self.__get_welpen_madchen()
        self.dogs["Welpen_und_Junghunde"] = self.__get_welpen_junghunde()
        self.dogs["Pflegestelle"] = self.__get_welpen_pflegestelle()
        return self.dogs


# create_report()
# create_pandoc()
# read_pandoc_csv()

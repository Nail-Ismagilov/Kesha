from elements_from_url import *

REIST_BALD = "*reist bald in sein Zuhause.", "*reist bald in ihr Zuhause."

class Dogs_from_URL:
    dogs = {}

    def __get_dogs(self, gender):
        pets = get_pets_from_url(urls[gender])
        dogs = []
        for pet in pets:
            if pet['spec'] not in REIST_BALD:
                html_text = requests.get(pet['url']).text
                soup = BeautifulSoup(html_text, 'html.parser')
                name = get_html_element(soup, NAME_HTML_PART, NAME_HTML_ATTRIBUTE)
                dogs.append(name)
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
    
    def dog_list(self):
        self.dogs["Hündinen"] = self.__get_hundin()
        self.dogs["Rüden"] = self.__get_ruden()
        self.dogs["Welpen_Madchen"] = self.__get_welpen_madchen()
        self.dogs["Welpen_und_Junghunde"] = self.__get_welpen_junghunde()
        self.dogs["Pflegestelle"] = self.__get_welpen_pflegestelle()
        return self.dogs
    
# class ManageFolders:
        
#     if not dog.dog_exist():
#         dog.create_dog()
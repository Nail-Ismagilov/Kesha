#!/usr/bin/python
import os
from elements_from_url import *
import re
import pathlib
import shutil


PFLEGESTELLE = "*befindet sich auf einer Pflegestelle in Deutschland."

class Dog:
    """Main class Dog with instance url and gender
    """
    def __init__(self, url, gender):
        self.url = url
        self.name = self.get_name()
        self.gender = gender
        # self.existedList = existedList

    def create_dog(self):
        self.create_folder(self.get_path())
        self.set_description()
        self.get_and_save_images()
    
    def delete_dog(self):
        path = self.get_path()
        self.del_path(path)

    def get_name(self):
        html_text = requests.get(self.url).text
        soup = BeautifulSoup(html_text, 'html.parser')
        name = get_html_element(soup, NAME_HTML_PART, NAME_HTML_ATTRIBUTE)
        return name  
    
    def get_description(self):
        html_text = requests.get(self.url).text
        soup = BeautifulSoup(html_text, 'html.parser')
        description = soup.find('div', attrs = {'id':'page-content'}).getText()
        return description

    def set_description(self):
        text_arr = []
        description = self.get_description()
        text_arr.append(description.split('wird nach positiver Vorkontrolle ')[0])
        self.compose_text(text_arr)

    def compose_text(self, text_arr):
        file = open("Maket.txt","r", encoding="utf-8")
        for word in file:
            word = re.sub("Name", f"{self.name}", word, flags=re.IGNORECASE)
            text_arr.append(word)
        file.close()
        composed_text = open(f"{self.get_path()}\{self.name}.txt", "w+", encoding="utf-8")
        for line in text_arr:
            composed_text.write(line)  

    def get_and_save_images(self):
        counter = 0
        html_text = requests.get(self.url).text
        soup = BeautifulSoup(html_text, 'html.parser')
        table = soup.find('div', attrs = {'class':'gal-container'})
        for line in table.findAll('div',attrs={'class':'img-box-shadow'}):
            image = line.a['href']
            counter += 1
            self.save_image(image, counter)
        pass
    
    def save_image(self, image_url, counter):
        img_data = requests.get(image_url).content
        with open(f"{self.get_path()}\{self.name}{counter}.jpg", 'wb') as handler:
            handler.write(img_data)
        pass

    def create_folder(self, path):
        os.makedirs(path) 

    def dog_exist(self):
        process = False
        if os.path.exists(self.get_path()):
            process = True
        else:
            process = False
        return process

    def get_path(self):
        path = f"{pathlib.Path(__file__).parent.resolve()}/hunde/{self.gender}/{self.name}"
        return path
    
    def del_path(self, path):
        shutil.rmtree(path)
        print(f"Dog folder deleted: {self.name}")

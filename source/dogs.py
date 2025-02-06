#!/usr/bin/python
import os
from source.elements_from_url import *
import re
import pathlib
import shutil
import random
from source.global_defines import DOGS_PATH    

PFLEGESTELLE = "*befindet sich auf einer Pflegestelle in Deutschland."
adjectives = {
    'male': ['Süßer', 'Schöner', 'Lieber'],
    'female': [ 'Süße', 'Schöne', 'Liebe']
}
endings = {
    'male': ['sucht seine Familie', 'sucht liebevolle Familie','sucht liebevolles Zuhause', 'sucht ein neues Zuhause'],
    'female': ['sucht ihre Familie', 'sucht liebevolle Familie', 'sucht liebevolles Zuhause', 'sucht ein neues Zuhause']
}
        

class Dog:
    """Main class Dog with instance url and gender
    """
    def __init__(self, dog, gender):
        self.url = dog['url']
        self.name = dog['name']
        self.gender = gender
        # self.existedList = existedList

    def create_dog(self):
        print(f"Creating dog: {self.name}")
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

    def get_title(self):
        is_male = self.gender in ['Rüden', 'Welpen_und_Junghunde']
        gender_key = 'male' if is_male else 'female'
        adj = random.choice(adjectives[gender_key])
        ending = random.choice(endings[gender_key])
        return f"{adj} {self.extract_name(self.get_description())} {ending}"

    def set_description(self):
        text_arr = []
        title = self.get_title()
        text_arr.append(f"{title}\n\n")  # Add title with double line break
        description = self.get_description()
        text_arr.append(description.split('wird nach positiver Vorkontrolle ')[0])
        self.compose_text(text_arr)

    def compose_text(self, text_arr):
        file = open("Maket.txt","r", encoding="utf-8")
        for word in file:
            word = re.sub("Name", f"{self.name}", word, flags=re.IGNORECASE)
            text_arr.append(word)
        file.close()
        composed_text = open(f"{self.get_path()}/{self.name}.txt", "w+", encoding="utf-8")
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
        with open(f"{self.get_path()}/{self.name}{counter}.jpg", 'wb') as handler:
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
        path = f"{DOGS_PATH}/{self.gender}/{self.name}"
        return path
    
    def del_path(self, path):
        shutil.rmtree(path)
        print(f"Dog folder deleted: {self.name}")

    def extract_name(self, text):
        # Use regex to find the line that starts with "Name:" and extract the name
        match = re.search(r"Name: (.+)", text)
        if match:
            return match.group(1)
        else:
            return 
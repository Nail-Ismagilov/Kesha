#!/usr/bin/python
import os
import sys
import requests
from bs4 import BeautifulSoup 
import re
import pathlib
import shutil

vermittlung = {'Hündinen' : 'https://tierschutzverein-kesha.de/vermittlung/huendinnen/',
               'Rüden' : 'https://tierschutzverein-kesha.de/vermittlung/ruede/',
               'Welpen_Madchen' : 'https://tierschutzverein-kesha.de/vermittlung/welpen-junghunde/',
               'Welpen_und_Junghunde' : 'https://tierschutzverein-kesha.de/welpen-junghunde-jungs/'}
PFLEGESTELLE = "*befindet sich auf einer Pflegestelle in Deutschland."

SPEC_HTML_PART      = 'span'
SPEC_HTML_ATTRIBUTE = {'style':"color: #4b90c9; display: block;"}
SPEC_HTML_ATTRIBUTE2 = {"style":"color: #4b90c9;"}
NAME_HTML_PART      = 'h2'
NAME_HTML_ATTRIBUTE = {'class':"entry-title"}

def get_html_element(html_text, element, attribute):
    value = ''
    for a in html_text.findAll(element, attrs = attribute):
        try:
            value = a.text
        except TypeError:
            value = 'N/A'
    return value

def get_pets_from_url(url):
    html_text = requests.get(url).text
    soup = BeautifulSoup(html_text, 'html.parser')
    table = soup.find('div', attrs = {'id':'page-content'})  
    
    dogs = []
    for row in table.findAll('blockquote', attrs = {'class':'pets'}):
        dog = {}
        try:
            dog['url'] = row.a['href']
            dog['spec'] = get_html_element(row, SPEC_HTML_PART, SPEC_HTML_ATTRIBUTE)
            if dog['spec'] == '':
                dog['spec'] = get_html_element(row, SPEC_HTML_PART, SPEC_HTML_ATTRIBUTE2)
        except TypeError:
            continue
        dogs.append(dog)
    return dogs

class Dog:
    """Main class Dog wit instace url and category(gender)
    """
    def __init__(self, url, category):
        self.url = url
        self.name = self.get_name()
        self.category = category

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

    def dog_exist(self, path):
        process = False
        if os.path.exists(path):
            process = True
        else:
            process = False
        return process

    def get_path(self):
        path = pathlib.Path(__file__).parent.resolve()/"hunde"/self.category/self.name
        return path
    
    def del_path(self, path):
        shutil.rmtree(path)
        print(f"Dog folder deleted: {self.name}")

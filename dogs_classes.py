#!/usr/bin/python
import os
import sys
import requests
from bs4 import BeautifulSoup 
import re
import pathlib
import shutil
from dogs import Dog
from doglist import Doglist

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

# dog dictionaries {"Dog_Name": "Dog_Path"}
NEW_DOG = {}
OLD_DOG = {}
HAPPY_DOG = {}
PFLEGESTELLE_DOG = {}

# main loop
HUNDINEN        = "1"
RUDEN           = "2"
WELPEN_RUDEN    = "3"
WELPEN_MADCHEN  = "4"
ALL             = "5"
EXIT            = "E"
WORD = "Maket.docx"
NEW_DOGS =[]
dogs_dict = {HUNDINEN: "Hündinen", RUDEN : "Rüden", WELPEN_RUDEN : "Welpen_und_Junghunde", WELPEN_MADCHEN : "Welpen_Madchen", ALL : "ALL"}


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

def dogs_still_exist(directory_path, key):
    """checks if the created directory name exist in Kesha Tierheim

    Args:
        directory_path (string): path to main tree
        key (string): subtree
    """
    #  Check if the folder name is not in the list
    for folder_name in os.listdir(f"{directory_path}/hunde/{key}"):
        exist = False
        folder_path = os.path.join(f"{directory_path}/hunde/", key, folder_name)
        if check_keys(folder_name, HAPPY_DOG):
            exist = True
            # print(f"{folder_name} is Happy Dog")
        elif check_keys(folder_name, OLD_DOG):
            exist = True
            # print(f"{folder_name} is still with us")
        elif check_keys(folder_name, NEW_DOG):
            exist = True
            # print(f"{folder_name} is new Dog")
        if not exist:
            # print(f"{folder_name} is not from pride")
            OLD_DOG[folder_name] = key
            print(f"Deleted folder: {folder_name}")
            print(f"folder path {folder_path}")
            shutil.rmtree(f"{folder_path}")

def check_keys(key, dogs):
    """checks if the key exist in the dictionary dogs"""
    if key in dogs.keys():
        return True
    else:
        return False
    

def print_output(text_file):
    """prints the text file"""
    # print file  
    with open(text_file, "r") as file:
        content = file.read()
    print("\n")
    print(content)

def create_report(path, gender, all = False):
    """creates report and saves it"""
    report = f"{path}/report/{gender}_report.txt"
    pflegestelle = f"{path}/report/pflegestelle_report.txt"       
    with open(report, "w", encoding="utf-8") as file:
        file.write("GEBLIEBEN:\n")
        for gender in vermittlung.keys():
            # file.write(f"  {gender}\n")
            dogs = [k for k, v in OLD_DOG.items() if v == gender]
            for dog in dogs:
                file.write("    * " + dog + "\n")
        file.write("\nABGEHOLT:\n")
        for gender in vermittlung.keys():
            # file.write(f"  {gender}\n")
            dogs = [k for k, v in HAPPY_DOG.items() if v == gender]
            for dog in dogs:
                file.write("    * " + dog + "\n")
        file.write("\nNEUE:\n")
        for gender in vermittlung.keys():
            # file.write(f"  {gender}\n")
            dogs = [k for k, v in NEW_DOG.items() if v == gender]
            for dog in dogs:
                file.write("    * " + dog + "\n")
    with open(pflegestelle, "w", encoding="utf-8") as file:    
        for gender in vermittlung.keys():
            dogs = [k for k, v in PFLEGESTELLE_DOG.items() if v == gender]
            for dog in dogs:
                file.write("    * " + dog + "\n")
        
    if not all:
        print_output(report)

def clear_dicts():
    """ clears all global dicts"""
    NEW_DOG.clear()
    HAPPY_DOG.clear()
    OLD_DOG.clear()
    PFLEGESTELLE_DOG.clear()

def start():
    """ Main method calling other methods
    """
    dogs = "0"
    all = False
    # female = Doglist("Hündinen")
    # male = Doglist("Rüden")
    # boys = Doglist("Welpen Rüden")
    # girls = Doglist("Welpen Mädchen")
    # list = [female, male, boys, girls]

    while (dogs.upper() != EXIT):
        print("vvvvvvvvvvvvvvvvvvvvvvvvvvvv")
        print("============================")
        print("Dogs:")
        print("1 - Hündinen\n"     + 
            "2 - Rüden\n"        +
            "3 - Welpen Rüden\n" +
            "4 - Welpen Mädchen\n"  +
            "5 - ALL\n"
            "E - Exit")
        print("============================")
        dogs = input("Select Dog: ")
        
        key = dogs_dict.get(dogs)
        print(f"Selected: {key}")
        if key == "ALL":
            all = True
        print("============================\n")
        if dogs.upper() != EXIT:
            for gender in list(vermittlung.keys()):
                if all:
                    key = gender  
                print (f"Gender is : {gender}")
                if key == gender:
                    doggies = get_pets_from_url(vermittlung[key])
                    for dog in doggies:
                        doggy = Dog(dog['url'], key)
                        if doggy.dog_exist(doggy.get_path()):
                            if dog['spec'] == '*reist bald in sein Zuhause.' or dog['spec'] == '*reist bald in ihr Zuhause.':
                                HAPPY_DOG[doggy.name] = key
                                doggy.delete_dog()
                                print(f"{doggy.name} - {dog['spec']}")
                            elif dog['spec'] == '*befindet sich auf einer Pflegestelle in Deutschland.':    
                                PFLEGESTELLE_DOG[doggy.name] = key
                            OLD_DOG[doggy.name] = key
                            # print(f"{doggy.name} exist")
                        else:
                            if dog['spec'] == '*reist bald in sein Zuhause.' or dog['spec'] == '*reist bald in ihr Zuhause.':
                                HAPPY_DOG[doggy.name] = key
                            else:
                                print(f"{doggy.name} does not exist")
                                doggy.create_dog()
                                NEW_DOG[doggy.name] = key
                    # path to the main tree
                    path = pathlib.Path(__file__).parent.resolve()
                    create_report(path, key, all)
                    # check if there old folders to be deleted
                    dogs_still_exist(path, key)
            if all:
                create_report(path, "ALL")
            clear_dicts()
            print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
start()
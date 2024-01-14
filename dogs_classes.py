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

REPORT_PATH = f"{pathlib.Path(__file__).parent.resolve()}/report"
DOGS_PATH = f"{pathlib.Path(__file__).parent.resolve()}/hunde"

REIST_BALD = "*reist bald in sein Zuhause.", "*reist bald in ihr Zuhause."
PFLEGESTELLE = "*befindet sich auf einer Pflegestelle in Deutschland."

## constants for finding elements in website
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

dogs_dict = {HUNDINEN: "Hündinen", 
             RUDEN : "Rüden", 
             WELPEN_RUDEN : "Welpen_und_Junghunde", 
             WELPEN_MADCHEN : "Welpen_Madchen", 
             ALL : "ALL", 
             EXIT : "Exit"}


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

def dogs_still_exist(key):
    """checks if the created directory name exist in Kesha Tierheim
    Args:
        key (string): subtree
    """
    #  Check if the folder name is not in the list
    for folder_name in os.listdir(f"{DOGS_PATH}/{key}"):
        exist = False
        folder_path = os.path.join(DOGS_PATH, key, folder_name)
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

def create_report(gender, all=False):
    """Creates a report and saves it to a file.

    Args:
        path (str): The path to the directory where the report files are stored.
        gender (str): The gender of the dogs to include in the report.
        all (bool): Whether to print the output to the console or not.

    Returns:
        None
    """
    report = f"{REPORT_PATH}/{gender}_report.txt"
    pflegestelle = f"{REPORT_PATH}/pflegestelle_report.txt"

    with open(report, "w", encoding="utf-8") as file:
        file.write("GEBLIEBEN:\n")
        for gender in vermittlung.keys():
            # file.write(f"  {gender}\n")
            dogs = [dog_name for dog_name, dog_gender in OLD_DOG.items() if dog_gender == gender]
            for dog in dogs:
                file.write("    * " + dog + "\n")

        file.write("\nABGEHOLT:\n")
        for gender in vermittlung.keys():
            # file.write(f"  {gender}\n")
            dogs = [dog_name for dog_name, dog_gender in HAPPY_DOG.items() if dog_gender == gender]
            for dog in dogs:
                file.write("    * " + dog + "\n")

        file.write("\nNEUE:\n")
        for gender in vermittlung.keys():
            # file.write(f"  {gender}\n")
            dogs = [dog_name for dog_name, dog_gender in NEW_DOG.items() if dog_gender == gender]
            for dog in dogs:
                file.write("    * " + dog + "\n")

    with open(pflegestelle, "a", encoding="utf-8") as file:
        for gender in vermittlung.keys():
            dogs = [dog_name for dog_name, dog_gender in PFLEGESTELLE_DOG.items() if dog_gender == gender]
            for dog in dogs:
                file.write("    * " + dog + "\n")

    with open(pflegestelle, "a", encoding="utf-8") as file:    
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

def clean_report():
    """ 
    """
    reports = [f for f in os.listdir(REPORT_PATH) if os.path.isfile(os.path.join(REPORT_PATH, f))]
    for report in reports:
        with open(report, "r+") as file:
            file.truncate(0)


def start():
    """Main method calling other methods"""
    user_choice = "0"
    all = False
    # Dictionary to store the mapping between the user input and the dog gender

    while (user_choice.upper() != EXIT):
        print("vvvvvvvvvvvvvvvvvvvvvvvvvvvv")
        print("============================")
        print("Dogs:")
        # Use f-strings to format the output
        print(f"1 - {dogs_dict[HUNDINEN]}\n"
              f"2 - {dogs_dict[RUDEN]}\n"
              f"3 - {dogs_dict[WELPEN_RUDEN]}\n"
              f"4 - {dogs_dict[WELPEN_MADCHEN]}\n"
              f"5 - {dogs_dict[ALL]}\n"
              f"{EXIT} - {dogs_dict[EXIT]}")

        print("============================")
        user_choice = input("Select Dog: ")

        key = dogs_dict.get(user_choice)
        print(f"Selected: {key}")
        if key == ALL:
            all = True

        print("============================\n")
        if user_choice.upper() != EXIT:
            for gender in vermittlung.keys():
                if all:
                    key = gender
                print(f"Gender is : {gender}")
                if key == gender:
                    pets = get_pets_from_url(vermittlung[key])
                    # Use list comprehensions to filter and transform the data
                    happy_dogs = [pet['name'] for pet in pets if pet['spec'] in REIST_BALD]
                    pflegestelle_dogs = [pet['name'] for pet in pets if pet['spec'] == PFLEGESTELLE]
                    old_dogs = [pet['name'] for pet in pets if Dog(pet['url'], key).dog_exist()]
                    new_dogs = [pet['name'] for pet in pets if pet['name'] not in old_dogs]

                    # Use the any() and all() functions to check the conditions
                    if any(happy_dogs):
                        for dog in happy_dogs:
                            pet = Dog(dog['url'], key)
                            pet.delete_dog()
                            print(f"{pet.name} - {dog['spec']}")

                    if any(pflegestelle_dogs):
                        for dog in pflegestelle_dogs:
                            pet = Dog(dog['url'], key)
                            print(f"{pet.name} - {dog['spec']}")

                    if any(old_dogs):
                        for dog in old_dogs:
                            pet = Dog(dog['url'], key)
                            print(f"{pet.name} exist")

                    if any(new_dogs):
                        for dog in new_dogs:
                            pet = Dog(dog['url'], key)
                            pet.create_dog()
                            print(f"{pet.name} does not exist")
                            
                    create_report(key, all)
                    # Use the pathlib module to work with file paths
                    dogs_still_exist(pathlib.Path(key))
            if all:
                create_report(ALL)
            clear_dicts()
            print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
start()
#!/usr/bin/python
from dogs import *
from doglist import *
from cli import *
from manage_folder import *
from report import *

dogsGender = ["Hündinen", "Rüden", "Welpen_Madchen", "Welpen_und_Junghunde"]

# main loop
def start():
    """Main method calling other methods"""
    user_choice = "0"

    # create dogs list
    dogList = Doglist()

    # create folders
    create_new_dogs()

    # deflete folders
    for gender in dogList.happy_dogs().keys():
        for dog in dogList.happy_dogs()[gender]:
            delete_dog(gender, dog)

    # create reports   
    create_report(dogList)
    
    # create CLI object
    cli = CLI()

    while (user_choice.upper() != EXIT):
        cli.create_menu()
        user_choice = input("Select Dog: ")
        if user_choice.upper() != EXIT and int(user_choice) <= len(dogsGender):
            show_report(dogsGender[int(user_choice)-1])

start()
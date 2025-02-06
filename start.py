#!/usr/bin/python
from source.dogs import *
from source.doglist import *
from source.cli import *
from source.manage_folder import *
from source.report import *

dogsGender = ["Hündinen", "Rüden", "Welpen_Madchen", "Welpen_und_Junghunde", "Pflegestelle"]

# main loop
def start():
    """Main method calling other methods"""
    user_choice = "0"
    
    # create CLI object
    cli = CLI()

    while (user_choice.upper() != EXIT):
        cli.create_menu()
        user_choice = input("Select Dog: ")
        if user_choice.upper() != EXIT and int(user_choice) <= len(dogsGender):
            gender = dogsGender[int(user_choice)-1]
            
            # create dogs list
            print("createing dogs list")
            dogList = Doglist(gender)

            # create reports
            print("createing dogs report")   
            create_report(dogList)

            print("createing new dogs")
            # create folders
            create_new_dogs(gender)

            # deflete folders
            for dog in dogList.happy_dogs():
                delete_dog(gender, dog)
            show_report(gender)

start()
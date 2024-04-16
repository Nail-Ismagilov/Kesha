#!/usr/bin/python
from dogs import *
from doglist import dogList
from cli import *

REPORT_PATH = f"{pathlib.Path(__file__).parent.resolve()}/report"
DOGS_PATH = f"{pathlib.Path(__file__).parent.resolve()}/hunde"



# main loop



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
        
    if not all:
        print_output(report)

def clean_report():
    """ 
    """
    reports = [f for f in os.listdir(REPORT_PATH) if os.path.isfile(os.path.join(REPORT_PATH, f))]
    for report in reports:
        with open(report, "r+") as file:
            file.truncate(0)

def delete_happy_dogs()
def start():
    """Main method calling other methods"""
    user_choice = "0"
    # Dictionary to store the mapping between the user input and the dog gender
    
    # create dogs list
    # create folders
    # deflete folders
    # create reports
   
    dogList.happy_dogs()
    cli = CLI()
    while (user_choice.upper() != EXIT):
        cli.create_dog()
        cli.create_menu()
        user_choice = input("Select Dog: ")

       
start()
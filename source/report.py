from source.dogs import *
from source.doglist import Doglist
from source.global_defines import REPORT_PATH
from source.manage_folder import ensure_folder_exists


def create_report(dogsList: Doglist, gender: str):
    """Creates a report and saves it to a file for the given gender.

    Args:
        dogsList (Doglist): The Doglist for the gender.
        gender (str): The gender of the dogs to include in the report.

    Returns:
        None
    """
    report = f"{REPORT_PATH}/{gender}_report.txt"
    ensure_folder_exists(REPORT_PATH)
    with open(report, "w", encoding="utf-8") as file:
        file.write("GEBLIEBEN:\n")
        for dog in dogsList.left_dogs():
            file.write("    * " + dog + "\n")

        file.write("\nABGEHOLT:\n")
        for dog in dogsList.happy_dogs():
            file.write("    * " + dog + "\n")

        file.write("\nNEUE:\n")
        for dog in  dogsList.new_dogs():
            file.write("    * " + dog + "\n")

def clean_report():
    """ 
    """
    reports = [f for f in os.listdir(REPORT_PATH) if os.path.isfile(os.path.join(REPORT_PATH, f))]
    for report in reports:
        with open(os.path.join(REPORT_PATH, report), "r+") as file:
            file.truncate(0)

def show_report(gender):
    file_path = f"{REPORT_PATH}/{gender}_report.txt"
    ensure_folder_exists(REPORT_PATH)
    try:
        with open(file_path, 'r') as file:
            # Read the content of the file
            file_content = file.read()
            
            # Print the content
            print(f"{gender}:\n", file_content)
    
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

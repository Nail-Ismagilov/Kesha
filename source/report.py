import os
from source.doglist import Doglist
from source.global_defines import REPORT_PATH, gender_display
from source.manage_folder import ensure_folder_exists
from datetime import datetime


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
    
    # Get current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(report, "w", encoding="utf-8") as file:
        file.write(f"Report created: {timestamp}\n")
        file.write("="*50 + "\n\n")
        
        file.write("GEBLIEBEN:\n")
        for dog in dogsList.left_dogs():
            file.write("    * " + dog + "\n")

        file.write("\nABGEHOLT:\n")
        for dog in dogsList.happy_dogs():
            file.write("    * " + dog + "\n")

        file.write("\nNEUE:\n")
        for dog in  dogsList.new_dogs():
            file.write("    * " + dog + "\n")

def show_report(gender):
    file_path = os.path.join(REPORT_PATH, f"{gender}_report.txt")
    ensure_folder_exists(REPORT_PATH)
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()
        # Single f-string (the old two-arg print injected a stray leading space).
        print(f"\n{gender_display(gender)}:\n{file_content}")
    except FileNotFoundError:
        print(f"Kein Report für {gender_display(gender)} gefunden.")
    except Exception as e:
        print(f"Fehler beim Lesen des Reports: {e}")

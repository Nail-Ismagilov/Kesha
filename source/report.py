from source.dogs import *
from source.doglist import Doglist
from source.global_defines import REPORT_PATH


def create_report(dogsList: Doglist):
    """Creates a report and saves it to a file.

    Args:
        path (str): The path to the directory where the report files are stored.
        gender (str): The gender of the dogs to include in the report.
        all (bool): Whether to print the output to the console or not.

    Returns:
        None
    """
    for gender in urls.keys():
        report = f"{REPORT_PATH}/{gender}_report.txt"

        # pflegestelle = f"{REPORT_PATH}/pflegestelle_report.txt"
        # print(f"gender = {gender}")
        with open(report, "w", encoding="utf-8") as file:
            file.write("GEBLIEBEN:\n")
            # file.write(f"  {gender}\n")
            for dog in dogsList.left_dogs()[gender]:
                file.write("    * " + dog + "\n")

            file.write("\nABGEHOLT:\n")
            for dog in dogsList.happy_dogs()[gender]:
                file.write("    * " + dog + "\n")

            file.write("\nNEUE:\n")
            for dog in  dogsList.new_dogs()[gender]:
                file.write("    * " + dog + "\n")

def clean_report():
    """ 
    """
    reports = [f for f in os.listdir(REPORT_PATH) if os.path.isfile(os.path.join(REPORT_PATH, f))]
    for report in reports:
        with open(report, "r+") as file:
            file.truncate(0)

def show_report(gender):
    file_path = f"{REPORT_PATH}/{gender}_report.txt"
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

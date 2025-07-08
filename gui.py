import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from source.doglist import Doglist
from source.manage_folder import create_new_dogs, delete_dog
from source.report import create_report
import source.report as report_module
import os

dogsGender = ["Hündinen", "Rüden", "Welpen_Madchen", "Welpen_und_Junghunde", "Pflegestelle"]

def process_gender(gender, output):
    output.insert(tk.END, f"\nProcessing: {gender}\n")
    output.insert(tk.END, "createing dogs list\n")
    dogList = Doglist(gender)
    output.insert(tk.END, "createing dogs report\n")
    create_report(dogList)
    output.insert(tk.END, "createing new dogs\n")
    create_new_dogs(gender)
    for dog in dogList.happy_dogs():
        delete_dog(gender, dog)
    show_report_gui(gender, output)
    output.insert(tk.END, f"Done with {gender}\n")
    output.see(tk.END)

def process_all(output):
    for gender in dogsGender:
        process_gender(gender, output)

def show_new_dogs(selected_gender, output):
    output.delete(1.0, tk.END)
    output.insert(tk.END, f"==== New Dogs for {selected_gender} ====\n\n")
    dogList = Doglist(selected_gender)
    if dogList.existingList:
        output.insert(tk.END, "Local dogs:\n")
        for dog in sorted(dogList.existingList):
            output.insert(tk.END, f"  • {dog}\n")
        output.insert(tk.END, "\n")
    if dogList.internetList:
        output.insert(tk.END, "Online dogs:\n")
        for dog in sorted(dogList.internetList):
            output.insert(tk.END, f"  • {dog}\n")
        output.insert(tk.END, "\n")
    new_dogs = dogList.new_dogs()
    output.insert(tk.END, "New dogs:\n")
    if new_dogs:
        for dog in sorted(new_dogs):
            output.insert(tk.END, f"  • {dog}\n")
    else:
        output.insert(tk.END, "  (None)\n")
    output.see(tk.END)

def show_gone_dogs(selected_gender, output):
    output.delete(1.0, tk.END)
    output.insert(tk.END, f"==== Gone Dogs for {selected_gender} ====\n\n")
    dogList = Doglist(selected_gender)
    if dogList.existingList:
        output.insert(tk.END, "Local dogs:\n")
        for dog in sorted(dogList.existingList):
            output.insert(tk.END, f"  • {dog}\n")
        output.insert(tk.END, "\n")
    if dogList.internetList:
        output.insert(tk.END, "Online dogs:\n")
        for dog in sorted(dogList.internetList):
            output.insert(tk.END, f"  • {dog}\n")
        output.insert(tk.END, "\n")
    gone_dogs = dogList.happy_dogs()
    output.insert(tk.END, "Gone dogs:\n")
    if gone_dogs:
        for dog in sorted(gone_dogs):
            output.insert(tk.END, f"  • {dog}\n")
    else:
        output.insert(tk.END, "  (None)\n")
    output.see(tk.END)

def show_report_gui(selected_gender, output):
    output.delete(1.0, tk.END)
    report_str = get_report_string(selected_gender)
    output.insert(tk.END, report_str)
    output.see(tk.END)

def get_report_string(gender):
    file_path = os.path.join(report_module.REPORT_PATH, f"{gender}_report.txt")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()
        return f"==== Report for {gender} ====" + "\n\n" + file_content
    except FileNotFoundError:
        return f"No report found for {gender}.\n"
    except Exception as e:
        return f"An error occurred: {e}\n"

def main():
    root = tk.Tk()
    root.title("Kesha Dog Manager")
    root.geometry("750x650")

    frame = tk.Frame(root)
    frame.pack(pady=10)

    output = ScrolledText(root, width=90, height=30, state='normal')
    output.pack(padx=10, pady=10)

    # Gender selection dropdown
    gender_var = tk.StringVar(value=dogsGender[0])
    gender_menu = tk.OptionMenu(root, gender_var, *dogsGender)
    gender_menu.pack(pady=5)

    # Button row
    button_frame = tk.Frame(root)
    button_frame.pack(pady=5)

    tk.Button(button_frame, text="Show New Dogs", width=18, command=lambda: show_new_dogs(gender_var.get(), output)).pack(side=tk.LEFT, padx=4)
    tk.Button(button_frame, text="Show Gone Dogs", width=18, command=lambda: show_gone_dogs(gender_var.get(), output)).pack(side=tk.LEFT, padx=4)
    tk.Button(button_frame, text="Show Report", width=18, command=lambda: show_report_gui(gender_var.get(), output)).pack(side=tk.LEFT, padx=4)

    # Main action buttons
    action_frame = tk.Frame(root)
    action_frame.pack(pady=5)
    for gender in dogsGender:
        btn = tk.Button(action_frame, text=gender, width=15, command=lambda g=gender: process_gender(g, output))
        btn.pack(side=tk.LEFT, padx=5)
    tk.Button(root, text="ALL", width=15, command=lambda: process_all(output)).pack(pady=5)
    tk.Button(root, text="Exit", width=15, command=root.destroy).pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    main() 
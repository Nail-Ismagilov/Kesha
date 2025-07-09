import customtkinter as ctk
from customtkinter import CTkFont, CTkTextbox
from source.doglist import Doglist
from source.manage_folder import create_new_dogs, delete_dog
from source.report import create_report
import source.report as report_module
import os
import webbrowser

dogsGender = ["Hündinen", "Rüden", "Welpen_Madchen", "Welpen_und_Junghunde", "Pflegestelle"]

# --- Helper for status bar ---
def set_status(status_var, msg):
    status_var.set(msg)

def process_gender(gender, output, status_var):
    set_status(status_var, f"Processing {gender}...")
    output.configure(state='normal')
    output.insert(ctk.END, f"\nProcessing: {gender}\n")
    output.insert(ctk.END, "createing dogs list\n")
    dogList = Doglist(gender)
    output.insert(ctk.END, "createing dogs report\n")
    create_report(dogList, gender)
    output.insert(ctk.END, "createing new dogs\n")
    create_new_dogs(gender)
    for dog in dogList.happy_dogs():
        delete_dog(gender, dog)
    show_report_gui(gender, output, status_var)
    output.insert(ctk.END, f"Done with {gender}\n")
    output.see(ctk.END)
    set_status(status_var, f"Done with {gender}.")
    output.configure(state='disabled')

def process_all(output, status_var):
    for gender in dogsGender:
        process_gender(gender, output, status_var)

def parse_report_section(report_text, section):
    # section: 'NEUE:' or 'ABGEHOLT:'
    lines = report_text.splitlines()
    in_section = False
    dogs = []
    for line in lines:
        if line.strip().upper() == section:
            in_section = True
            continue
        if in_section:
            if line.strip() == '' or line.strip().endswith(':'):
                break
            if line.strip().startswith('*'):
                dogs.append(line.strip().lstrip('*').strip())
    return dogs

def show_new_and_gone_dogs(selected_gender, output, status_var):
    set_status(status_var, f"Showing new and gone dogs for {selected_gender}")
    # Set background color to match report window
    output.configure(fg_color=output.cget('fg_color'))  # Use the same as in report window (default or custom)
    output.configure(state='normal')
    output.delete(1.0, ctk.END)
    if selected_gender == "ALL":
        for gender in dogsGender:
            report_str = get_report_string(gender)
            new_dogs = parse_report_section(report_str, 'NEUE:')
            gone_dogs = parse_report_section(report_str, 'ABGEHOLT:')
            output.insert(ctk.END, f"==== New Dogs (from report) for {gender} ====" + "\n\n", 'header')
            if new_dogs:
                for dog in new_dogs:
                    tag_name = f"new_{gender}_{dog}"
                    output.insert(ctk.END, f"🐶 ", (f"{tag_name}_emoji", tag_name, 'new', 'doglink'))
                    output.insert(ctk.END, f"{dog}\n", (f"{tag_name}_name", tag_name, 'new', 'doglink'))
                    def callback(event, g=gender, d=dog):
                        folder_path = os.path.join('hunde', g, d)
                        try:
                            os.startfile(folder_path)
                        except Exception as e:
                            print(f"[ERROR] Could not open folder: {folder_path} ({e})")
                    output.tag_bind(f"{tag_name}_name", '<Enter>', lambda e, t=tag_name, d=dog: (
                        output.tag_remove('doglink_hover', '1.0', 'end'),
                        output.tag_add('doglink_hover', f"{e.widget.index('current').split('.')[0]}.{int(e.widget.index('current').split('.')[1])}", f"{e.widget.index('current').split('.')[0]}.{int(e.widget.index('current').split('.')[1])+len(d)}"),
                        output.configure(cursor='hand2')
                    ))
                    output.tag_bind(f"{tag_name}_name", '<Leave>', lambda e, t=tag_name: (
                        output.tag_remove('doglink_hover', '1.0', 'end'),
                        output.configure(cursor='')
                    ))
                    output.tag_bind(tag_name, '<Button-1>', callback)
            else:
                output.insert(ctk.END, "(None)\n", 'none')
            output.insert(ctk.END, "\n\n", 'section')
            output.insert(ctk.END, f"==== Happy Dogs (from report) for {gender} ====" + "\n\n", 'header')
            if gone_dogs:
                for dog in gone_dogs:
                    tag_name = f"gone_{gender}_{dog}"
                    output.insert(ctk.END, f"🐶 ", (f"{tag_name}_emoji", tag_name, 'gone', 'doglink'))
                    output.insert(ctk.END, f"{dog}\n", (f"{tag_name}_name", tag_name, 'gone', 'doglink'))
                    def callback(event, g=gender, d=dog):
                        folder_path = os.path.join('hunde', g, d)
                        try:
                            os.startfile(folder_path)
                        except Exception as e:
                            print(f"[ERROR] Could not open folder: {folder_path} ({e})")
                    output.tag_bind(f"{tag_name}_name", '<Enter>', lambda e, t=tag_name, d=dog: (
                        output.tag_remove('doglink_hover', '1.0', 'end'),
                        output.tag_add('doglink_hover', f"{e.widget.index('current').split('.')[0]}.{int(e.widget.index('current').split('.')[1])}", f"{e.widget.index('current').split('.')[0]}.{int(e.widget.index('current').split('.')[1])+len(d)}"),
                        output.configure(cursor='hand2')
                    ))
                    output.tag_bind(f"{tag_name}_name", '<Leave>', lambda e, t=tag_name: (
                        output.tag_remove('doglink_hover', '1.0', 'end'),
                        output.configure(cursor='')
                    ))
                    output.tag_bind(tag_name, '<Button-1>', callback)
            else:
                output.insert(ctk.END, "(None)\n", 'none')
            output.insert(ctk.END, "\n" + ("="*60) + "\n\n", 'section')
    else:
        report_str = get_report_string(selected_gender)
        new_dogs = parse_report_section(report_str, 'NEUE:')
        gone_dogs = parse_report_section(report_str, 'ABGEHOLT:')
        output.insert(ctk.END, f"==== New Dogs (from report) for {selected_gender} ====" + "\n\n", 'header')
        if new_dogs:
            for dog in new_dogs:
                tag_name = f"new_{selected_gender}_{dog}"
                output.insert(ctk.END, f"🐶 ", (f"{tag_name}_emoji", tag_name, 'new', 'doglink'))
                output.insert(ctk.END, f"{dog}\n", (f"{tag_name}_name", tag_name, 'new', 'doglink'))
                def callback(event, g=selected_gender, d=dog):
                    folder_path = os.path.join('hunde', g, d)
                    try:
                        os.startfile(folder_path)
                    except Exception as e:
                        print(f"[ERROR] Could not open folder: {folder_path} ({e})")
                output.tag_bind(f"{tag_name}_name", '<Enter>', lambda e, t=tag_name, d=dog: (
                    output.tag_remove('doglink_hover', '1.0', 'end'),
                    output.tag_add('doglink_hover', f"{e.widget.index('current').split('.')[0]}.{int(e.widget.index('current').split('.')[1])}", f"{e.widget.index('current').split('.')[0]}.{int(e.widget.index('current').split('.')[1])+len(d)}"),
                    output.configure(cursor='hand2')
                ))
                output.tag_bind(f"{tag_name}_name", '<Leave>', lambda e, t=tag_name: (
                    output.tag_remove('doglink_hover', '1.0', 'end'),
                    output.configure(cursor='')
                ))
                output.tag_bind(tag_name, '<Button-1>', callback)
        else:
            output.insert(ctk.END, "(None)\n", 'none')
        output.insert(ctk.END, "\n\n", 'section')
        output.insert(ctk.END, f"==== Happy Dogs (from report) for {selected_gender} ====" + "\n\n", 'header')
        if gone_dogs:
            for dog in gone_dogs:
                tag_name = f"gone_{selected_gender}_{dog}"
                output.insert(ctk.END, f"🐶 ", (f"{tag_name}_emoji", tag_name, 'gone', 'doglink'))
                output.insert(ctk.END, f"{dog}\n", (f"{tag_name}_name", tag_name, 'gone', 'doglink'))
                def callback(event, g=selected_gender, d=dog):
                    folder_path = os.path.join('hunde', g, d)
                    try:
                        os.startfile(folder_path)
                    except Exception as e:
                        print(f"[ERROR] Could not open folder: {folder_path} ({e})")
                output.tag_bind(f"{tag_name}_name", '<Enter>', lambda e, t=tag_name, d=dog: (
                    output.tag_remove('doglink_hover', '1.0', 'end'),
                    output.tag_add('doglink_hover', f"{e.widget.index('current').split('.')[0]}.{int(e.widget.index('current').split('.')[1])}", f"{e.widget.index('current').split('.')[0]}.{int(e.widget.index('current').split('.')[1])+len(d)}"),
                    output.configure(cursor='hand2')
                ))
                output.tag_bind(f"{tag_name}_name", '<Leave>', lambda e, t=tag_name: (
                    output.tag_remove('doglink_hover', '1.0', 'end'),
                    output.configure(cursor='')
                ))
                output.tag_bind(tag_name, '<Button-1>', callback)
        else:
            output.insert(ctk.END, "(None)\n", 'none')
    output.see(ctk.END)
    set_status(status_var, f"Displayed new and gone dogs for {selected_gender} (from report).")
    output.configure(state='disabled')

def show_new_dogs(selected_gender, output, status_var):
    set_status(status_var, f"Showing new dogs for {selected_gender}")
    output.configure(state='normal')
    output.delete(1.0, ctk.END)
    report_str = get_report_string(selected_gender)
    new_dogs = parse_report_section(report_str, 'NEUE:')
    output.insert(ctk.END, f"==== New Dogs (from report) for {selected_gender} ====" + "\n\n", 'header')
    if new_dogs:
        for dog in new_dogs:
            output.insert(ctk.END, f"🐶 {dog}\n", 'new')
    else:
        output.insert(ctk.END, "(None)\n", 'none')
    output.see(ctk.END)
    set_status(status_var, f"Displayed new dogs for {selected_gender} (from report).")
    output.configure(state='disabled')

def show_gone_dogs(selected_gender, output, status_var):
    set_status(status_var, f"Showing gone dogs for {selected_gender}")
    output.configure(state='normal')
    output.delete(1.0, ctk.END)
    report_str = get_report_string(selected_gender)
    gone_dogs = parse_report_section(report_str, 'ABGEHOLT:')
    output.insert(ctk.END, f"==== Gone Dogs (from report) for {selected_gender} ====" + "\n\n", 'header')
    if gone_dogs:
        for dog in gone_dogs:
            output.insert(ctk.END, f"🐶 {dog}\n", 'gone')
    else:
        output.insert(ctk.END, "(None)\n", 'none')
    output.see(ctk.END)
    set_status(status_var, f"Displayed gone dogs for {selected_gender} (from report).")
    output.configure(state='disabled')

def show_report_gui(selected_gender, output, status_var):
    set_status(status_var, f"Showing report for {selected_gender}")
    output.configure(state='normal')
    output.delete(1.0, ctk.END)
    if selected_gender == "ALL":
        for gender in dogsGender:
            report_str = get_report_string(gender)
            output.insert(ctk.END, report_str, 'header')
            output.insert(ctk.END, "\n" + ("="*60) + "\n\n", 'section')
    else:
        report_str = get_report_string(selected_gender)
        output.insert(ctk.END, report_str, 'header')
    output.see(ctk.END)
    set_status(status_var, f"Displayed report for {selected_gender}.")
    output.configure(state='disabled')

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

# Add helpers to enable/disable buttons

def set_buttons_state(buttons, state):
    for btn in buttons:
        btn.configure(state=state)

# Update process_selected to show 'Processing...' on the Process button and disable all action buttons

def process_selected(selected_option, output, status_var, action_buttons, progress_bar):
    set_buttons_state(action_buttons, ctk.DISABLED)
    orig_text = action_buttons[2].cget('text')
    action_buttons[2].configure(text='Processing...')
    output.configure(state='normal')
    output.insert(ctk.END, '\n[Processing... Please wait]\n', 'section')
    output.see(ctk.END)
    output.configure(state='disabled')
    output.update()  # Force update so message is visible
    # Also update the root window to ensure all widgets refresh
    output.winfo_toplevel().update()
    # Show and start progress bar
    progress_bar.pack(side="bottom", pady=(0, 20), anchor="w")
    progress_bar.start()
    try:
        if selected_option == "ALL":
            process_all(output, status_var)
            show_report_gui('ALL', output, status_var)
        else:
            process_gender(selected_option, output, status_var)
    finally:
        set_buttons_state(action_buttons, ctk.NORMAL)
        action_buttons[2].configure(text=orig_text)
        set_status(status_var, "Ready.")
        # Stop and hide progress bar
        progress_bar.stop()
        progress_bar.pack_forget()

def main():
    ctk.set_appearance_mode("system")  # or 'dark' or 'light'
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.title("Kesha Dog Manager")
    root.geometry("950x800")

    # Fonts
    header_font = CTkFont(family="Arial", size=18, weight="bold")
    section_font = CTkFont(family="Arial", size=13, weight="bold")
    mono_font = CTkFont(family="Consolas", size=13)
    large_dog_font = CTkFont(family="Arial", size=20, weight="bold")

    # Title
    title = ctk.CTkLabel(root, text="Kesha Dog Manager", font=header_font)
    title.pack(pady=(10, 0))

    # Option selection (gender or ALL)
    option_frame = ctk.CTkFrame(root, fg_color="transparent")
    option_frame.pack(pady=10)
    option_label = ctk.CTkLabel(option_frame, text="Select Option:", font=section_font)
    option_label.pack(side="left", padx=5)
    options = dogsGender + ["ALL"]
    option_var = ctk.StringVar(value=options[0])
    option_menu = ctk.CTkComboBox(option_frame, variable=option_var, values=options, width=200, font=mono_font, state="readonly")
    option_menu.pack(side="left", padx=5)

    # Create a frame on the left for all buttons
    left_frame = ctk.CTkFrame(root, fg_color="transparent")
    left_frame.pack(side="left", fill="y", padx=10, pady=10, anchor="n")

    # Main action buttons (vertical)
    btn_process = ctk.CTkButton(left_frame, text="Wooff!", width=180, command=lambda: process_selected(option_var.get(), output, status_var, action_buttons, progress_bar))
    btn_process.pack(side="top", pady=4, anchor="w")
    btn_new_gone = ctk.CTkButton(left_frame, text="New & Happy", width=180, command=lambda: show_new_and_gone_dogs(option_var.get(), output, status_var))
    btn_new_gone.pack(side="top", pady=4, anchor="w")
    btn_report = ctk.CTkButton(left_frame, text="Report", width=180, command=lambda: show_report_gui(option_var.get(), output, status_var))
    btn_report.pack(side="top", pady=4, anchor="w")
    action_buttons = [btn_new_gone, btn_report, btn_process]

    # Website buttons (vertical, under main buttons)
    def open_quoke():
        webbrowser.open('https://quoka.de')

    def open_kesha():
        webbrowser.open('https://tierschutzverein-kesha.de')

    btn_quoke = ctk.CTkButton(left_frame, text="Quoka", width=180, command=open_quoke)
    btn_kesha = ctk.CTkButton(left_frame, text="Kesha Website", width=180, command=open_kesha)
    btn_quoke.pack(side="top", pady=4, anchor="w")
    btn_kesha.pack(side="top", pady=4, anchor="w")

    # Progress bar (hidden by default)
    progress_bar = ctk.CTkProgressBar(left_frame, width=180, mode='indeterminate')
    progress_bar.pack(side="bottom", pady=(0, 20), anchor="w")
    progress_bar.pack_forget()  # Hide initially

    # Remove individual gender buttons
    # Main action buttons (removed)
    # action_frame = ttk.Frame(root)
    # action_frame.pack(pady=10)
    # for gender in dogsGender:
    #     ttk.Button(action_frame, text=gender, width=15, command=lambda g=gender: process_gender(g, output, status_var)).pack(side=tk.LEFT, padx=5)
    # ttk.Button(root, text="ALL", width=15, command=lambda: process_all(output, status_var)).pack(pady=5)

    btn_exit = ctk.CTkButton(left_frame, text="Exit", width=180, command=root.destroy)
    btn_exit.pack(side="bottom", pady=10, anchor="w")

    # Output area
    output_frame = ctk.CTkFrame(root, fg_color="transparent")
    output_frame.pack(padx=10, pady=10, fill="both", expand=True)
    output = CTkTextbox(output_frame, width=1000, height=600, font=mono_font, wrap="word")
    output.pack(fill="both", expand=True)
    output.configure(state="disabled")

    # Tag styles for output
    output.tag_config('header', foreground='#ffffff')
    output.tag_config('section', foreground='#e0e0e0')
    output.tag_config('local', foreground='#cccccc')
    output.tag_config('online', foreground='#bbbbbb')
    output.tag_config('new', foreground='#7CFC00')  # light green
    output.tag_config('gone', foreground='#FF6347') # light red
    output.tag_config('none', foreground='#dddddd')
    output.tag_config('doglink', background='#f0f0f0', borderwidth=1, relief='raised', foreground='#0077cc', underline=True, lmargin1=18, lmargin2=18, spacing1=6, spacing3=6)
    output.tag_config('doglink_hover', background='#b3e5fc', borderwidth=1, relief='raised', foreground='#005999', underline=True, lmargin1=18, lmargin2=18, spacing1=6, spacing3=6)

    # Set default text color to white for the output area
    output.configure(text_color="#ffffff")

    # Status bar
    status_var = ctk.StringVar()
    status_bar = ctk.CTkLabel(root, textvariable=status_var, anchor="w", font=mono_font)
    status_bar.pack(fill="x", side="bottom", ipady=2)
    set_status(status_var, "Ready.")

    root.mainloop()

if __name__ == "__main__":
    main() 
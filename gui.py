import customtkinter as ctk
from customtkinter import CTkFont, CTkTextbox
from source.doglist import Doglist
from source.manage_folder import create_new_dogs, delete_dog
from source.report import create_report
from source.global_defines import DOGS_PATH
import source.report as report_module
import os
import sys
import subprocess
import threading
import webbrowser
from datetime import datetime

dogsGender = ["Hündinen", "Rüden", "Welpen_Madchen", "Welpen_und_Junghunde", "Pflegestelle"]

# --- Helper for status bar ---
def set_status(status_var, msg):
    status_var.set(msg)

def _append_output(output, msg):
    """Append text to the output box. MUST be called on the Tk main thread."""
    output.configure(state='normal')
    output.insert(ctk.END, msg)
    output.see(ctk.END)
    output.configure(state='disabled')

# Fraction of the bar reserved for the upfront scan pass (finding out how
# many new dogs actually need downloading), before any real work starts.
SCAN_WEIGHT = 0.05
WORK_WEIGHT = 1.0 - SCAN_WEIGHT

def process_gender(gender, dogList, log, on_dog_progress):
    """Process one already-scanned gender. `on_dog_progress` is called once per
    real unit of work completed (one new dog downloaded, or one adopted dog's
    folder deleted) so the bar reflects actual work, not a fixed per-gender slice."""
    log(f"\nProcessing: {gender}\n")
    log("creating dogs report\n")
    create_report(dogList, gender)

    log("creating new dogs\n")
    create_new_dogs(gender, dogList.pets, on_dog_done=on_dog_progress)

    for dog in dogList.happy_dogs():
        delete_dog(gender, dog)
        on_dog_progress()

    log(f"Done with {gender}\n")

def process_all(log, progress):
    """progress(fraction) reports 0..1 completion across the whole run.

    Phase 1 scans every gender (one listing fetch + local diff each - cheap,
    no downloads) to find out exactly how many new dogs need downloading and
    how many adopted dogs need deleting. Phase 2 does that work, advancing the
    bar per dog. A gender with nothing new to download (e.g. Rüden or Welpen
    coming back empty) contributes nothing to the total instead of reserving
    a fixed slice of the bar it never uses.
    """
    log("Checking all categories for new dogs...\n")
    doglists = []
    for i, gender in enumerate(dogsGender, start=1):
        doglists.append((gender, Doglist(gender)))
        progress(SCAN_WEIGHT * i / len(dogsGender))

    total_new = sum(len(dl.new_dogs()) for _, dl in doglists)
    total_happy = sum(len(dl.happy_dogs()) for _, dl in doglists)
    total_work = total_new + total_happy
    log(f"Found {total_new} new dog(s) to download, {total_happy} to remove.\n")

    if not total_work:
        progress(1.0)  # nothing to download or delete anywhere - done
        for gender, dogList in doglists:
            process_gender(gender, dogList, log, lambda: None)
        return

    done = [0]

    def on_dog_progress():
        done[0] += 1
        progress(SCAN_WEIGHT + WORK_WEIGHT * (done[0] / total_work))

    for gender, dogList in doglists:
        process_gender(gender, dogList, log, on_dog_progress)

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

def get_report_timestamp(report_text):
    # Extract timestamp from report text
    lines = report_text.splitlines()
    for line in lines:
        if line.startswith('Report created:'):
            return line.replace('Report created:', '').strip()
    return None

def show_statistics_dashboard(root):
    # Create a new window for statistics
    stats_window = ctk.CTkToplevel(root)
    stats_window.title("📊 Statistics Dashboard")
    stats_window.geometry("600x500")
    stats_window.transient(root)
    
    # Header
    header = ctk.CTkLabel(stats_window, text="📊 Kesha Statistics Dashboard", 
                         font=CTkFont(family="Arial", size=20, weight="bold"))
    header.pack(pady=20)
    
    # Create frame for statistics
    stats_frame = ctk.CTkFrame(stats_window)
    stats_frame.pack(padx=20, pady=10, fill="both", expand=True)
    
    # Gather statistics
    total_new = 0
    total_happy = 0
    total_stayed = 0
    stats_by_gender = {}
    
    for gender in dogsGender:
        report_str = get_report_string(gender)
        new_dogs = parse_report_section(report_str, 'NEUE:')
        happy_dogs = parse_report_section(report_str, 'ABGEHOLT:')
        stayed_dogs = parse_report_section(report_str, 'GEBLIEBEN:')
        
        stats_by_gender[gender] = {
            'new': len(new_dogs),
            'happy': len(happy_dogs),
            'stayed': len(stayed_dogs),
            'timestamp': get_report_timestamp(report_str)
        }
        
        total_new += len(new_dogs)
        total_happy += len(happy_dogs)
        total_stayed += len(stayed_dogs)
    
    # Display overall statistics
    overall_frame = ctk.CTkFrame(stats_frame)
    overall_frame.pack(padx=10, pady=10, fill="x")
    
    overall_label = ctk.CTkLabel(overall_frame, text="Overall Statistics", 
                                font=CTkFont(family="Arial", size=16, weight="bold"))
    overall_label.pack(pady=5)
    
    # Create cards for overall stats
    cards_frame = ctk.CTkFrame(overall_frame)
    cards_frame.pack(pady=10)
    
    # New dogs card
    new_card = ctk.CTkFrame(cards_frame, fg_color="#7CFC00", width=150, height=80)
    new_card.pack(side="left", padx=10)
    new_card.pack_propagate(False)
    ctk.CTkLabel(new_card, text="🆕 New Dogs", font=CTkFont(size=14, weight="bold")).pack(pady=5)
    ctk.CTkLabel(new_card, text=str(total_new), font=CTkFont(size=24, weight="bold")).pack()
    
    # Happy dogs card
    happy_card = ctk.CTkFrame(cards_frame, fg_color="#FF6347", width=150, height=80)
    happy_card.pack(side="left", padx=10)
    happy_card.pack_propagate(False)
    ctk.CTkLabel(happy_card, text="🎊 Happy Dogs", font=CTkFont(size=14, weight="bold")).pack(pady=5)
    ctk.CTkLabel(happy_card, text=str(total_happy), font=CTkFont(size=24, weight="bold")).pack()
    
    # Stayed dogs card
    stayed_card = ctk.CTkFrame(cards_frame, fg_color="#4169E1", width=150, height=80)
    stayed_card.pack(side="left", padx=10)
    stayed_card.pack_propagate(False)
    ctk.CTkLabel(stayed_card, text="🏠 Stayed", font=CTkFont(size=14, weight="bold")).pack(pady=5)
    ctk.CTkLabel(stayed_card, text=str(total_stayed), font=CTkFont(size=24, weight="bold")).pack()
    
    # Display by gender
    gender_label = ctk.CTkLabel(stats_frame, text="Statistics by Category", 
                               font=CTkFont(family="Arial", size=16, weight="bold"))
    gender_label.pack(pady=10)
    
    # Create scrollable frame for gender stats
    scroll_frame = ctk.CTkScrollableFrame(stats_frame, height=200)
    scroll_frame.pack(padx=10, pady=5, fill="both", expand=True)
    
    for gender, stats in stats_by_gender.items():
        gender_frame = ctk.CTkFrame(scroll_frame)
        gender_frame.pack(padx=5, pady=5, fill="x")
        
        # Gender name and timestamp
        header_frame = ctk.CTkFrame(gender_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(header_frame, text=f"📁 {gender}", 
                    font=CTkFont(size=14, weight="bold")).pack(side="left")
        if stats['timestamp']:
            ctk.CTkLabel(header_frame, text=f"Last updated: {stats['timestamp']}", 
                        font=CTkFont(size=10), text_color="gray").pack(side="right")
        
        # Stats for this gender
        stats_text = f"New: {stats['new']} | Happy: {stats['happy']} | Stayed: {stats['stayed']}"
        ctk.CTkLabel(gender_frame, text=stats_text, font=CTkFont(size=12)).pack(padx=10, pady=5)
    
    # Refresh button
    refresh_btn = ctk.CTkButton(stats_window, text="🔄 Refresh Stats", 
                               command=lambda: (stats_window.destroy(), show_statistics_dashboard(root)))
    refresh_btn.pack(pady=10)
    
    # Close button  
    close_btn = ctk.CTkButton(stats_window, text="Close", command=stats_window.destroy)
    close_btn.pack(pady=(0, 10))



def open_dog_folder(gender, dog):
    folder_path = os.path.join(DOGS_PATH, gender, dog)
    try:
        if sys.platform.startswith('win'):
            os.startfile(folder_path)
        elif sys.platform == 'darwin':
            subprocess.run(['open', folder_path])
        else:
            subprocess.run(['xdg-open', folder_path])
    except Exception as e:
        print(f"[ERROR] Could not open folder: {folder_path} ({e})")

def insert_dog_link(output, emoji, gender, dog, tag_prefix, extra_tag):
    """Insert a clickable dog name that opens its local folder on click."""
    tag_name = f"{tag_prefix}_{gender}_{dog}"
    output.insert(ctk.END, f"{emoji} ", (f"{tag_name}_emoji", tag_name, extra_tag, 'doglink'))
    output.insert(ctk.END, f"{dog}\n", (f"{tag_name}_name", tag_name, extra_tag, 'doglink'))

    def callback(event, g=gender, d=dog):
        open_dog_folder(g, d)

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

def show_new_dogs(output, status_var, search_term=""):
    set_status(status_var, "Showing new dogs for ALL")
    output.configure(state='normal')
    output.delete(1.0, ctk.END)
    
    # Statistics variables
    total_new = 0
    filtered_count = 0
    
    for gender in dogsGender:
        report_str = get_report_string(gender)
        timestamp = get_report_timestamp(report_str)
        new_dogs = parse_report_section(report_str, 'NEUE:')
        output.insert(ctk.END, f"==== New Dogs for {gender} ====\n", 'header')
        if timestamp:
            output.insert(ctk.END, f"Report created: {timestamp}\n\n", 'timestamp')
        if new_dogs:
            total_new += len(new_dogs)
            dogs_to_show = [dog for dog in new_dogs if search_term.lower() in dog.lower()] if search_term else new_dogs
            filtered_count += len(dogs_to_show)
            
            for dog in dogs_to_show:
                insert_dog_link(output, "🐶", gender, dog, "new", 'new')
        else:
            output.insert(ctk.END, "(None)\n", 'none')
        output.insert(ctk.END, "\n" + ("="*60) + "\n\n", 'section')
    # Show statistics at the end
    if search_term:
        output.insert(ctk.END, f"\n📊 Search Results: {filtered_count} dogs found matching '{search_term}' (out of {total_new} total new dogs)\n", 'stats')
    else:
        output.insert(ctk.END, f"\n📊 Total New Dogs: {total_new}\n", 'stats')
    
    output.see(1.0)  # Scroll to top instead of bottom
    set_status(status_var, f"Found {filtered_count if search_term else total_new} new dogs" + (f" matching '{search_term}'" if search_term else ""))
    output.configure(state='disabled')

def show_gone_dogs(output, status_var, search_term=""):
    set_status(status_var, "Showing happy dogs for ALL")
    output.configure(state='normal')
    output.delete(1.0, ctk.END)
    
    # Statistics variables
    total_happy = 0
    filtered_count = 0
    
    for gender in dogsGender:
        report_str = get_report_string(gender)
        timestamp = get_report_timestamp(report_str)
        gone_dogs = parse_report_section(report_str, 'ABGEHOLT:')
        output.insert(ctk.END, f"==== Happy Dogs for {gender} ====\n", 'header')
        if timestamp:
            output.insert(ctk.END, f"Report created: {timestamp}\n\n", 'timestamp')
        if gone_dogs:
            total_happy += len(gone_dogs)
            dogs_to_show = [dog for dog in gone_dogs if search_term.lower() in dog.lower()] if search_term else gone_dogs
            filtered_count += len(dogs_to_show)
            
            for dog in dogs_to_show:
                output.insert(ctk.END, f"🐶 {dog}\n", 'gone')
        else:
            output.insert(ctk.END, "(None)\n", 'none')
        output.insert(ctk.END, "\n" + ("="*60) + "\n\n", 'section')
    # Show statistics at the end
    if search_term:
        output.insert(ctk.END, f"\n🎉 Search Results: {filtered_count} dogs found matching '{search_term}' (out of {total_happy} total happy adoptions)\n", 'stats')
    else:
        output.insert(ctk.END, f"\n🎉 Total Happy Adoptions: {total_happy}\n", 'stats')
    
    output.see(1.0)  # Scroll to top instead of bottom
    set_status(status_var, f"Found {filtered_count if search_term else total_happy} happy dogs" + (f" matching '{search_term}'" if search_term else ""))
    output.configure(state='disabled')

def show_stayed_dogs(output, status_var, search_term=""):
    set_status(status_var, "Showing stayed dogs for ALL")
    output.configure(state='normal')
    output.delete(1.0, ctk.END)

    # Statistics variables
    total_stayed = 0
    filtered_count = 0

    for gender in dogsGender:
        report_str = get_report_string(gender)
        timestamp = get_report_timestamp(report_str)
        stayed_dogs = parse_report_section(report_str, 'GEBLIEBEN:')
        output.insert(ctk.END, f"==== Stayed Dogs for {gender} ====\n", 'header')
        if timestamp:
            output.insert(ctk.END, f"Report created: {timestamp}\n\n", 'timestamp')
        if stayed_dogs:
            total_stayed += len(stayed_dogs)
            dogs_to_show = [dog for dog in stayed_dogs if search_term.lower() in dog.lower()] if search_term else stayed_dogs
            filtered_count += len(dogs_to_show)

            for dog in dogs_to_show:
                insert_dog_link(output, "🏠", gender, dog, "stayed", 'stayed')
        else:
            output.insert(ctk.END, "(None)\n", 'none')
        output.insert(ctk.END, "\n" + ("="*60) + "\n\n", 'section')
    # Show statistics at the end
    if search_term:
        output.insert(ctk.END, f"\n🏠 Search Results: {filtered_count} dogs found matching '{search_term}' (out of {total_stayed} total stayed dogs)\n", 'stats')
    else:
        output.insert(ctk.END, f"\n🏠 Total Stayed Dogs: {total_stayed}\n", 'stats')

    output.see(1.0)  # Scroll to top instead of bottom
    set_status(status_var, f"Found {filtered_count if search_term else total_stayed} stayed dogs" + (f" matching '{search_term}'" if search_term else ""))
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

def _set_progress(progress_bar, progress_label, fraction):
    """Update the determinate progress bar + its percentage label.
    MUST be called on the Tk main thread."""
    progress_bar.set(fraction)
    progress_label.configure(text=f"{round(fraction * 100)}%")

def process_selected(root, output, status_var, action_buttons, progress_frame, progress_bar, progress_label):
    set_buttons_state(action_buttons, ctk.DISABLED)
    orig_text = action_buttons[0].cget('text')
    action_buttons[0].configure(text='Processing...')
    set_status(status_var, "Processing...")
    output.configure(state='normal')
    output.delete(1.0, ctk.END)  # Clear the output window
    output.insert(ctk.END, '\n[Processing... Please wait]\n', 'section')
    output.see(ctk.END)
    output.configure(state='disabled')
    # Show the progress bar+label. It advances smoothly now because the heavy
    # work runs on a worker thread, leaving the Tk event loop free to redraw.
    progress_frame.pack(side="bottom", pady=(0, 20), anchor="w")
    _set_progress(progress_bar, progress_label, 0)

    def set_fraction(fraction):
        # Called from the worker thread -> hop back to the Tk main thread.
        root.after(0, lambda: _set_progress(progress_bar, progress_label, fraction))

    def log(msg):
        # Called from the worker thread -> hop back to the Tk main thread.
        root.after(0, lambda: _append_output(output, msg))

    def done():
        show_report_gui('ALL', output, status_var)
        set_buttons_state(action_buttons, ctk.NORMAL)
        action_buttons[0].configure(text=orig_text)
        set_status(status_var, "Ready.")
        progress_frame.pack_forget()

    def worker():
        try:
            process_all(log, set_fraction)
        except Exception as e:
            root.after(0, lambda: _append_output(output, f"\n[ERROR] {e}\n"))
        finally:
            root.after(0, done)

    threading.Thread(target=worker, daemon=True).start()

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

    # Create a frame on the left for all buttons
    left_frame = ctk.CTkFrame(root, fg_color="transparent")
    left_frame.pack(side="left", fill="y", padx=10, pady=10, anchor="n")

    # Search bar
    search_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
    search_label = ctk.CTkLabel(search_frame, text="🔍 Search Dogs:", font=section_font)
    search_label.pack(side="top", anchor="w", pady=(0,2))
    search_var = ctk.StringVar()
    search_entry = ctk.CTkEntry(search_frame, textvariable=search_var, width=180, placeholder_text="Type dog name...")
    search_entry.pack(side="top", anchor="w")
    search_frame.pack(side="top", pady=(0, 15), anchor="w")
    
    # Main action buttons (vertical)
    btn_process = ctk.CTkButton(left_frame, text="🚀 Wooff!", width=180, command=lambda: process_selected(root, output, status_var, action_buttons, progress_frame, progress_bar, progress_label))
    btn_process.pack(side="top", pady=4, anchor="w")
    btn_new = ctk.CTkButton(left_frame, text="🆕 New Dogs", width=180, command=lambda: show_new_dogs(output, status_var, search_var.get()))
    btn_new.pack(side="top", pady=4, anchor="w")
    btn_happy = ctk.CTkButton(left_frame, text="🎊 Happy Dogs", width=180, command=lambda: show_gone_dogs(output, status_var, search_var.get()))
    btn_happy.pack(side="top", pady=4, anchor="w")
    btn_stayed = ctk.CTkButton(left_frame, text="🏠 Stayed Dogs", width=180, command=lambda: show_stayed_dogs(output, status_var, search_var.get()))
    btn_stayed.pack(side="top", pady=4, anchor="w")
    btn_stats = ctk.CTkButton(left_frame, text="📊 Statistics", width=180, command=lambda: show_statistics_dashboard(root))
    btn_stats.pack(side="top", pady=4, anchor="w")
    action_buttons = [btn_process, btn_new, btn_happy, btn_stayed]
    
    # Bind Enter key in search to trigger new dogs search
    search_entry.bind('<Return>', lambda e: show_new_dogs(output, status_var, search_var.get()))

    # Website buttons (vertical, under main buttons)
    def open_quoke():
        webbrowser.open('https://quoka.de')

    def open_kesha():
        webbrowser.open('https://tierschutzverein-kesha.de')

    btn_quoke = ctk.CTkButton(left_frame, text="Quoka", width=180, command=open_quoke)
    btn_kesha = ctk.CTkButton(left_frame, text="Kesha Website", width=180, command=open_kesha)
    btn_quoke.pack(side="top", pady=4, anchor="w")
    btn_kesha.pack(side="top", pady=4, anchor="w")

    # Progress bar + percentage label (hidden by default)
    progress_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
    progress_label = ctk.CTkLabel(progress_frame, text="0%", font=CTkFont(size=11))
    progress_bar = ctk.CTkProgressBar(progress_frame, width=180, mode='determinate')
    progress_label.pack(side="top", anchor="w")
    progress_bar.pack(side="top", pady=(2, 0))
    progress_frame.pack(side="bottom", pady=(0, 20), anchor="w")
    progress_frame.pack_forget()  # Hide initially

    # Remove individual gender buttons
    # Main action buttons (removed)
    # action_frame = ttk.Frame(root)
    # action_frame.pack(pady=10)
    # for gender in dogsGender:
    #     ttk.Button(action_frame, text=gender, width=15, command=lambda g=gender: process_gender(g, output, status_var)).pack(side=tk.LEFT, padx=5)
    # ttk.Button(root, text="ALL", width=15, command=lambda: process_all(output, status_var)).pack(pady=5)

    # Keyboard shortcuts info
    shortcuts_text = "⌨️ Shortcuts:\nCtrl+N: New Dogs\nCtrl+H: Happy Dogs\nCtrl+G: Stayed Dogs\nCtrl+W: Wooff!\nCtrl+S: Statistics\nCtrl+F: Focus Search\nEsc: Clear Search"
    shortcuts_label = ctk.CTkLabel(left_frame, text=shortcuts_text, font=('Arial', 10), justify="left", text_color="#666666")
    shortcuts_label.pack(side="bottom", pady=(10, 5), anchor="w")
    
    btn_exit = ctk.CTkButton(left_frame, text="❌ Exit", width=180, command=root.destroy)
    btn_exit.pack(side="bottom", pady=10, anchor="w")
    
    # Bind keyboard shortcuts
    root.bind('<Control-n>', lambda e: show_new_dogs(output, status_var, search_var.get()))
    root.bind('<Control-h>', lambda e: show_gone_dogs(output, status_var, search_var.get()))
    root.bind('<Control-g>', lambda e: show_stayed_dogs(output, status_var, search_var.get()))
    root.bind('<Control-w>', lambda e: process_selected(root, output, status_var, action_buttons, progress_frame, progress_bar, progress_label))
    root.bind('<Control-f>', lambda e: search_entry.focus())
    root.bind('<Control-s>', lambda e: show_statistics_dashboard(root))
    root.bind('<Escape>', lambda e: (search_var.set(''), output.focus()))

    # Output area
    output_frame = ctk.CTkFrame(root, fg_color="transparent")
    output_frame.pack(padx=10, pady=10, fill="both", expand=True)
    output = CTkTextbox(output_frame, width=1000, height=600, font=mono_font, wrap="word")
    output.pack(fill="both", expand=True)
    output.configure(state="disabled")

    # Tag styles for output
    output.tag_config('header', foreground='#2a4d69')
    output.tag_config('section', foreground='#e0e0e0')
    output.tag_config('local', foreground='#cccccc')
    output.tag_config('online', foreground='#bbbbbb')
    output.tag_config('new', foreground='#7CFC00')  # light green
    output.tag_config('gone', foreground='#FF6347') # light red
    output.tag_config('stayed', foreground='#5dade2')  # light blue for stayed dogs
    output.tag_config('none', foreground='#dddddd')
    output.tag_config('timestamp', foreground='#999999')  # gray for timestamps
    output.tag_config('stats', foreground='#4169E1')  # royal blue for statistics
    output.tag_config('doglink', background='#f0f0f0', borderwidth=1, relief='raised', foreground='#0077cc', underline=True, lmargin1=18, lmargin2=18, spacing1=6, spacing3=6)
    output.tag_config('doglink_hover', background='#b3e5fc', borderwidth=1, relief='raised', foreground='#005999', underline=True, lmargin1=18, lmargin2=18, spacing1=6, spacing3=6)

    # Set default text color to white for the output area
    output.configure(text_color="#2a4d69")

    # Status bar
    status_var = ctk.StringVar()
    status_bar = ctk.CTkLabel(root, textvariable=status_var, anchor="w", font=mono_font)
    status_bar.pack(fill="x", side="bottom", ipady=2)
    set_status(status_var, "Ready.")

    root.mainloop()

if __name__ == "__main__":
    main() 
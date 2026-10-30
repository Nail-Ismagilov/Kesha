import customtkinter as ctk
from customtkinter import CTkFont, CTkTextbox
from tkinter import messagebox
from source.doglist import Doglist
from source.manage_folder import create_new_dogs, delete_dog
from source.report import create_report
from source.dogs_from_url import REIST_BALD
from source.dogwatch_adapter import run_dogwatch, parse_changed_entries
from source.global_defines import DOGS_PATH, gender_display
import source.report as report_module
import os
import sys
import subprocess
import threading
import webbrowser

dogsGender = ["Hündinen", "Rüden", "Welpen_Madchen", "Welpen_und_Junghunde", "Pflegestelle"]
ALL_LABEL = "Alle"

# Fraction of the bar reserved for the upfront scan pass (finding out how
# many new dogs actually need downloading), before any real work starts.
SCAN_WEIGHT = 0.05
WORK_WEIGHT = 1.0 - SCAN_WEIGHT

# Proportional deletion guard: if a scrape would delete more than this fraction
# of a category's existing folders (and the category is non-trivially sized),
# treat it as a probable broken/partial scrape and refuse to delete. This is the
# defence against a half-loaded page classifying real dogs as "adopted".
MAX_DELETE_FRACTION = 0.5
MIN_FOLDERS_FOR_GUARD = 5


# --------------------------------------------------------------------------- #
# Theme-aware colours
# --------------------------------------------------------------------------- #
# Every value is a (light, dark) pair. CTk widgets accept the tuple directly and
# pick the right one for the current appearance mode. The classic-Tk text tags
# don't, so we resolve them per render via _pick() and re-apply on each redraw.
PALETTE = {
    "base":      ("#1a3a52", "#dfe9f2"),
    "header":    ("#1a3a52", "#7fb8e6"),
    "section":   ("#c2c2c2", "#4a4a4a"),   # subtle separators
    "new":       ("#2e7d32", "#66bb6a"),
    "gone":      ("#c0392b", "#ff7043"),
    "stayed":    ("#1565c0", "#5dade2"),
    "none":      ("#8a8a8a", "#9e9e9e"),
    "timestamp": ("#9e9e9e", "#8a8a8a"),
    "stats":     ("#1565c0", "#64b5f6"),
}
DANGER_FG = ("#c0392b", "#a93226")
DANGER_HOVER = ("#a93226", "#7b241c")


def _is_dark():
    return ctk.get_appearance_mode() == "Dark"


def _pick(key):
    light, dark = PALETTE[key]
    return dark if _is_dark() else light


def _configure_output_tags(output):
    """(Re)apply the textbox tag colours for the current light/dark mode.

    Called at the start of every render so switching OS themes never leaves
    dark-on-dark or white-on-white text.
    """
    output.configure(text_color=PALETTE["base"])
    for key in ("header", "section", "new", "gone", "stayed", "none", "timestamp", "stats"):
        output.tag_config(key, foreground=_pick(key))
    dl_bg = "#2b3a4a" if _is_dark() else "#e3f2fd"
    dl_fg = "#8ecbff" if _is_dark() else "#0066cc"
    hover_bg = "#37474f" if _is_dark() else "#b3e5fc"
    common = dict(underline=True, lmargin1=18, lmargin2=18, spacing1=4, spacing3=4)
    output.tag_config("doglink", background=dl_bg, foreground=dl_fg, **common)
    output.tag_config("doglink_hover", background=hover_bg, foreground=dl_fg, **common)


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def set_status(status_var, msg):
    status_var.set(msg)


def _append_output(output, msg):
    """Append text to the output box. MUST be called on the Tk main thread."""
    output.configure(state="normal")
    output.insert(ctk.END, msg)
    output.see(ctk.END)
    output.configure(state="disabled")


def _set_progress(progress_bar, progress_label, fraction):
    """Update the determinate progress bar + its percentage label.
    MUST be called on the Tk main thread."""
    progress_bar.set(fraction)
    progress_label.configure(text=f"{round(fraction * 100)}%")


def set_buttons_state(buttons, state):
    for btn in buttons:
        try:
            btn.configure(state=state)
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Scan / apply (no side effects during scan)
# --------------------------------------------------------------------------- #
class GenderPlan:
    """The outcome of scanning one category: what a run *would* create/delete."""

    def __init__(self, gender, doglist=None, error=None):
        self.gender = gender
        self.doglist = doglist
        self.error = error
        self.new = doglist.new_dogs() if doglist else []
        self.happy = doglist.happy_dogs() if doglist else []
        self.existing = doglist.existingList if doglist else []
        self.online_count = len(doglist.internetList) if doglist else 0
        # Proportional guard: block deletions that look like a broken scrape.
        self.delete_blocked = bool(
            doglist
            and len(self.existing) >= MIN_FOLDERS_FOR_GUARD
            and self.happy
            and len(self.happy) / len(self.existing) > MAX_DELETE_FRACTION
        )


def scan_all(log, progress=None):
    """Scan every category (listing fetch + local diff). No folders are written
    or deleted. Each category is isolated: one failing scrape doesn't abort the
    rest, it just yields a plan flagged with an error."""
    plans = []
    for i, gender in enumerate(dogsGender, start=1):
        try:
            plans.append(GenderPlan(gender, doglist=Doglist(gender)))
        except Exception as e:
            log(f"[FEHLER] {gender_display(gender)}: Abruf fehlgeschlagen ({e})\n")
            plans.append(GenderPlan(gender, error=str(e)))
        if progress:
            progress(SCAN_WEIGHT * i / len(dogsGender))
    return plans


def _new_summary():
    return {
        "created": 0, "failed": 0, "no_images": 0,
        "deleted": 0, "delete_failed": 0, "delete_skipped": 0, "scrape_failed": 0,
    }


def apply_all(plans, log, progress):
    """Execute the plans: (re)write reports, create new dogs, delete adopted ones
    (unless blocked). Returns a summary dict of what actually happened."""
    total_work = sum(
        len(p.new) + (0 if p.delete_blocked else len(p.happy))
        for p in plans if not p.error
    )
    done = [0]

    def tick():
        done[0] += 1
        if total_work:
            progress(SCAN_WEIGHT + WORK_WEIGHT * (done[0] / total_work))

    summary = _new_summary()
    for p in plans:
        display = gender_display(p.gender)
        if p.error:
            summary["scrape_failed"] += 1
            log(f"\n{display}: übersprungen (Abruf fehlgeschlagen) – Report unverändert.\n")
            continue

        log(f"\n{display}:\n")
        # Only overwrite the report when the scrape is trustworthy. A suspected
        # partial scrape keeps its previous (good) report instead of asserting
        # stale/wrong data with a fresh timestamp.
        if not p.delete_blocked:
            create_report(p.doglist, p.gender)

        c, f, ni = create_new_dogs(p.gender, p.doglist.pets, on_dog_done=tick, log=log)
        summary["created"] += c
        summary["failed"] += f
        summary["no_images"] += ni

        if p.delete_blocked:
            summary["delete_skipped"] += len(p.happy)
            log(f"  ⚠ Löschen & Report übersprungen: nur {p.online_count} von "
                f"{len(p.existing)} Hunden geladen (mögliche Störung).\n")
            continue

        for dog in p.happy:
            if delete_dog(p.gender, dog):
                summary["deleted"] += 1
                log(f"  🗑 {dog}: entfernt\n")
            else:
                summary["delete_failed"] += 1
                log(f"  ✗ {dog}: konnte nicht entfernt werden\n")
            tick()

    if not total_work:
        progress(1.0)
    return summary


def summarize_plans(plans):
    """Return (lines, n_new, n_del, n_blocked, n_error) for previews/dialogs."""
    lines = []
    n_new = n_del = n_blocked = n_error = 0
    for p in plans:
        d = gender_display(p.gender)
        if p.error:
            n_error += 1
            lines.append(f"⚠ {d}: Abruf fehlgeschlagen")
            continue
        n_new += len(p.new)
        if p.delete_blocked:
            n_blocked += len(p.happy)
            lines.append(f"{d}: +{len(p.new)} neu, {len(p.happy)} abgeholt "
                         f"⚠ (Löschen gesperrt)")
        else:
            n_del += len(p.happy)
            lines.append(f"{d}: +{len(p.new)} neu, −{len(p.happy)} abgeholt")
    return lines, n_new, n_del, n_blocked, n_error


def _summary_line(summary):
    parts = [f"Erstellt: {summary['created']}", f"Gelöscht: {summary['deleted']}"]
    if summary["failed"]:
        parts.append(f"Fehlgeschlagen: {summary['failed']}")
    if summary["no_images"]:
        parts.append(f"Ohne Bilder: {summary['no_images']}")
    if summary["delete_failed"]:
        parts.append(f"Löschen fehlgeschlagen: {summary['delete_failed']}")
    if summary["delete_skipped"]:
        parts.append(f"Löschen gesperrt: {summary['delete_skipped']}")
    if summary["scrape_failed"]:
        parts.append(f"Abruf fehlgeschlagen: {summary['scrape_failed']}")
    return " · ".join(parts)


# --------------------------------------------------------------------------- #
# Report parsing / display
# --------------------------------------------------------------------------- #
def parse_report_section(report_text, section):
    # section: 'NEUE:' / 'ABGEHOLT:' / 'GEBLIEBEN:' (upper-case)
    lines = report_text.splitlines()
    in_section = False
    dogs = []
    for line in lines:
        if line.strip().upper() == section:
            in_section = True
            continue
        if in_section:
            if line.strip() == "" or line.strip().endswith(":"):
                break
            if line.strip().startswith("*"):
                dogs.append(line.strip().lstrip("*").strip())
    return dogs


def get_report_timestamp(report_text):
    for line in report_text.splitlines():
        if line.startswith("Report created:"):
            return line.replace("Report created:", "").strip()
    return None


def get_report_string(gender):
    file_path = os.path.join(report_module.REPORT_PATH, f"{gender}_report.txt")
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            file_content = file.read()
        return f"==== Report: {gender_display(gender)} ====\n\n" + file_content
    except FileNotFoundError:
        return f"Kein Report für {gender_display(gender)} gefunden.\n"
    except Exception as e:
        return f"Fehler beim Lesen des Reports: {e}\n"


def open_dog_folder(gender, dog):
    folder_path = os.path.join(DOGS_PATH, gender, dog)
    try:
        if sys.platform.startswith("win"):
            os.startfile(folder_path)  # noqa: for Windows only
        elif sys.platform == "darwin":
            subprocess.run(["open", folder_path])
        else:
            subprocess.run(["xdg-open", folder_path])
    except Exception as e:
        print(f"[ERROR] Could not open folder: {folder_path} ({e})")


def insert_dog_link(output, emoji, gender, dog):
    """Insert a clickable dog name that opens its local folder on click.

    The emoji is inserted separately and left untagged so that astral-plane
    emoji widths never corrupt the character-index maths used for the link range
    (the old implementation was fragile for exactly that reason).
    """
    output.insert(ctk.END, f"{emoji} ")
    output.insert(ctk.END, dog + "\n")
    end_idx = output.index(f"{ctk.END}-2c")            # the '\n' we just added
    start_idx = output.index(f"{end_idx}-{len(dog)}c")  # names are BMP -> len is exact
    tag_name = f"link::{gender}::{dog}"
    output.tag_add("doglink", start_idx, end_idx)
    output.tag_add(tag_name, start_idx, end_idx)
    output.tag_bind(tag_name, "<Button-1>", lambda e, g=gender, d=dog: open_dog_folder(g, d))
    output.tag_bind(tag_name, "<Enter>", lambda e, s=start_idx, en=end_idx: (
        output.tag_add("doglink_hover", s, en), output.configure(cursor="hand2")))
    output.tag_bind(tag_name, "<Leave>", lambda e, s=start_idx, en=end_idx: (
        output.tag_remove("doglink_hover", s, en), output.configure(cursor="")))


def show_category(output, status_var, section, title, emoji, tag, clickable,
                  search_term="", gender_filter="ALL"):
    """Render one report section (NEUE / ABGEHOLT / GEBLIEBEN), optionally
    filtered to a single category and/or a search term."""
    _configure_output_tags(output)
    output.configure(state="normal")
    output.delete(1.0, ctk.END)

    genders = dogsGender if gender_filter == "ALL" else [gender_filter]
    total = 0
    shown = 0
    have_report = False
    for gender in genders:
        report_str = get_report_string(gender)
        if not report_str.startswith("Kein Report"):
            have_report = True
        timestamp = get_report_timestamp(report_str)
        dogs = parse_report_section(report_str, section)
        output.insert(ctk.END, f"{title} – {gender_display(gender)}\n", "header")
        if timestamp:
            output.insert(ctk.END, f"Stand: {timestamp}\n", "timestamp")
        if dogs:
            total += len(dogs)
            to_show = [d for d in dogs if search_term.lower() in d.lower()] if search_term else dogs
            shown += len(to_show)
            if to_show:
                for dog in to_show:
                    if clickable:
                        insert_dog_link(output, emoji, gender, dog)
                    else:
                        output.insert(ctk.END, f"{emoji} {dog}\n", tag)
            else:
                output.insert(ctk.END, "  (keine Treffer)\n", "none")
        else:
            output.insert(ctk.END, "  (keine)\n", "none")
        output.insert(ctk.END, "\n")

    if not have_report:
        output.insert(ctk.END,
                      "\nNoch keine Daten. Führe „🔍 Änderungen prüfen“ oder "
                      "„🔄 Aktualisieren“ aus.\n", "none")
    elif search_term:
        output.insert(ctk.END, f"\n📊 {shown} von {total} Treffer für „{search_term}“\n", "stats")
    else:
        output.insert(ctk.END, f"\n📊 Gesamt: {total}\n", "stats")

    output.see(1.0)
    output.configure(state="disabled")
    if search_term:
        set_status(status_var, f"{shown} von {total} für „{search_term}“ ({title})")
    else:
        set_status(status_var, f"{total} × {title}")


def show_new_dogs(output, status_var, search_term="", gender_filter="ALL"):
    show_category(output, status_var, "NEUE:", "Neue Hunde", "🐶", "new", True,
                  search_term, gender_filter)


def show_gone_dogs(output, status_var, search_term="", gender_filter="ALL"):
    # Adopted dogs' folders are deleted, so there is nothing to open -> not clickable.
    show_category(output, status_var, "ABGEHOLT:", "Abgeholt", "🎊", "gone", False,
                  search_term, gender_filter)


def show_stayed_dogs(output, status_var, search_term="", gender_filter="ALL"):
    show_category(output, status_var, "GEBLIEBEN:", "Geblieben", "🏠", "stayed", True,
                  search_term, gender_filter)


def show_changed_dogs(output, status_var, search_term="", gender_filter="ALL"):
    """Dogs dogwatch found changed (description / price / first photo / photo
    count), each with its reasons. The dog is still in the shelter, so the name
    is clickable."""
    _configure_output_tags(output)
    output.configure(state="normal")
    output.delete(1.0, ctk.END)

    genders = dogsGender if gender_filter == "ALL" else [gender_filter]
    total = 0
    shown = 0
    have_report = False
    for gender in genders:
        report_str = get_report_string(gender)
        if not report_str.startswith("Kein Report"):
            have_report = True
        timestamp = get_report_timestamp(report_str)
        entries = parse_changed_entries(report_str)
        output.insert(ctk.END, f"Geänderte Hunde – {gender_display(gender)}\n", "header")
        if timestamp:
            output.insert(ctk.END, f"Stand: {timestamp}\n", "timestamp")
        total += len(entries)
        to_show = ([e for e in entries if search_term.lower() in e[0].lower()]
                   if search_term else entries)
        shown += len(to_show)
        if to_show:
            for name, reason in to_show:
                insert_dog_link(output, "📝", gender, name)
                if reason:
                    output.insert(ctk.END, f"      → {reason}\n", "stayed")
        else:
            output.insert(ctk.END, "  (keine Treffer)\n" if entries else "  (keine)\n", "none")
        output.insert(ctk.END, "\n")

    if not have_report:
        output.insert(ctk.END,
                      "\nNoch keine Daten. Führe „🐶 Wooff!“ aus; die Änderungsprüfung läuft "
                      "danach im Hintergrund.\n", "none")
    elif search_term:
        output.insert(ctk.END, f"\n📊 {shown} von {total} Treffer für „{search_term}“\n", "stats")
    else:
        output.insert(ctk.END, f"\n📊 Gesamt: {total}\n", "stats")

    output.see(1.0)
    output.configure(state="disabled")
    if search_term:
        set_status(status_var, f"{shown} von {total} für „{search_term}“ (Geänderte Hunde)")
    else:
        set_status(status_var, f"{total} × Geänderte Hunde")


def _render_preview(output, plans):
    """Read-only preview of what a run WOULD change (nothing is written)."""
    _configure_output_tags(output)
    output.configure(state="normal")
    output.delete(1.0, ctk.END)
    output.insert(ctk.END, "Änderungsvorschau – es wurde nichts geändert\n\n", "header")
    for p in plans:
        d = gender_display(p.gender)
        if p.error:
            output.insert(ctk.END, f"⚠ {d}: Abruf fehlgeschlagen\n\n", "gone")
            continue
        output.insert(ctk.END, f"{d}\n", "header")
        if p.new:
            for name in p.new:
                output.insert(ctk.END, f"  🆕 {name}\n", "new")
        if p.happy:
            tag = "none" if p.delete_blocked else "gone"
            for name in p.happy:
                suffix = " (gesperrt)" if p.delete_blocked else ""
                output.insert(ctk.END, f"  🗑 {name}{suffix}\n", tag)
        if not p.new and not p.happy:
            output.insert(ctk.END, "  (keine Änderungen)\n", "none")
        if p.delete_blocked:
            output.insert(ctk.END,
                          f"  ⚠ Nur {p.online_count} von {len(p.existing)} Hunden geladen – "
                          f"Löschen gesperrt.\n", "gone")
        output.insert(ctk.END, "\n")
    output.see(1.0)
    output.configure(state="disabled")


def confirm_apply(root, lines, n_new, n_del, n_blocked, n_error):
    """Modal confirmation before any deletion. Returns True to proceed."""
    dialog = ctk.CTkToplevel(root)
    dialog.title("Änderungen bestätigen")
    dialog.geometry("500x460")
    dialog.minsize(440, 400)
    dialog.transient(root)
    dialog.grab_set()
    result = {"ok": False}

    ctk.CTkLabel(dialog, text="Folgende Änderungen werden ausgeführt:",
                 font=CTkFont(size=15, weight="bold")).pack(pady=(16, 8), padx=16, anchor="w")

    box = ctk.CTkScrollableFrame(dialog, height=200)
    box.pack(fill="both", expand=True, padx=16)
    for ln in lines:
        ctk.CTkLabel(box, text=ln, anchor="w", justify="left").pack(fill="x", anchor="w", pady=1)

    ctk.CTkLabel(dialog, text=f"Insgesamt: {n_new} erstellen, {n_del} löschen",
                 font=CTkFont(size=13, weight="bold")).pack(pady=(10, 0), padx=16, anchor="w")
    if n_blocked:
        ctk.CTkLabel(dialog, text=f"⚠ {n_blocked} Löschung(en) gesperrt (mögliche Störung).",
                     text_color=DANGER_FG).pack(padx=16, anchor="w")
    if n_error:
        ctk.CTkLabel(dialog, text=f"⚠ {n_error} Kategorie(n) nicht erreichbar.",
                     text_color=DANGER_FG).pack(padx=16, anchor="w")
    ctk.CTkLabel(dialog, text="Löschen verschiebt Ordner in den Papierkorb, wenn möglich.",
                 text_color=("gray40", "gray60"), font=CTkFont(size=11)).pack(
        padx=16, anchor="w", pady=(4, 0))

    btns = ctk.CTkFrame(dialog, fg_color="transparent")
    btns.pack(pady=14)

    def confirm():
        result["ok"] = True
        dialog.destroy()

    def cancel():
        result["ok"] = False
        dialog.destroy()

    ctk.CTkButton(btns, text="🔄 Aktualisieren", command=confirm,
                  fg_color=DANGER_FG, hover_color=DANGER_HOVER).pack(side="left", padx=8)
    ctk.CTkButton(btns, text="Abbrechen", command=cancel,
                  fg_color=("gray70", "gray30"), hover_color=("gray60", "gray40")).pack(side="left", padx=8)

    dialog.protocol("WM_DELETE_WINDOW", cancel)
    dialog.after(50, dialog.lift)
    root.wait_window(dialog)
    return result["ok"]


# --------------------------------------------------------------------------- #
# Statistics dashboard
# --------------------------------------------------------------------------- #
def show_statistics_dashboard(root):
    stats_window = ctk.CTkToplevel(root)
    stats_window.title("📊 Statistik")
    stats_window.geometry("620x520")
    stats_window.minsize(560, 480)
    stats_window.transient(root)

    ctk.CTkLabel(stats_window, text="📊 Kesha Statistik",
                 font=CTkFont(family="Arial", size=20, weight="bold")).pack(pady=20)

    stats_frame = ctk.CTkFrame(stats_window)
    stats_frame.pack(padx=20, pady=10, fill="both", expand=True)

    total_new = total_happy = total_stayed = 0
    stats_by_gender = {}
    for gender in dogsGender:
        report_str = get_report_string(gender)
        stats_by_gender[gender] = {
            "new": len(parse_report_section(report_str, "NEUE:")),
            "happy": len(parse_report_section(report_str, "ABGEHOLT:")),
            "stayed": len(parse_report_section(report_str, "GEBLIEBEN:")),
            "timestamp": get_report_timestamp(report_str),
        }
        total_new += stats_by_gender[gender]["new"]
        total_happy += stats_by_gender[gender]["happy"]
        total_stayed += stats_by_gender[gender]["stayed"]

    overall_frame = ctk.CTkFrame(stats_frame)
    overall_frame.pack(padx=10, pady=10, fill="x")
    ctk.CTkLabel(overall_frame, text="Gesamt",
                 font=CTkFont(family="Arial", size=16, weight="bold")).pack(pady=5)

    cards_frame = ctk.CTkFrame(overall_frame, fg_color="transparent")
    cards_frame.pack(pady=10, fill="x")
    for i in range(3):
        cards_frame.grid_columnconfigure(i, weight=1)

    def make_card(col, color, label, value):
        card = ctk.CTkFrame(cards_frame, fg_color=color, height=84)
        card.grid(row=0, column=col, padx=8, sticky="ew")
        card.grid_propagate(False)
        ctk.CTkLabel(card, text=label, text_color="white",
                     font=CTkFont(size=14, weight="bold")).pack(pady=(10, 0))
        ctk.CTkLabel(card, text=str(value), text_color="white",
                     font=CTkFont(size=24, weight="bold")).pack()

    make_card(0, "#2e7d32", "🆕 Neu", total_new)
    make_card(1, "#c0392b", "🎊 Abgeholt", total_happy)
    make_card(2, "#1565c0", "🏠 Geblieben", total_stayed)

    ctk.CTkLabel(stats_frame, text="Nach Kategorie",
                 font=CTkFont(family="Arial", size=16, weight="bold")).pack(pady=10)

    scroll_frame = ctk.CTkScrollableFrame(stats_frame, height=200)
    scroll_frame.pack(padx=10, pady=5, fill="both", expand=True)
    for gender, stats in stats_by_gender.items():
        gender_frame = ctk.CTkFrame(scroll_frame)
        gender_frame.pack(padx=5, pady=5, fill="x")
        header_frame = ctk.CTkFrame(gender_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(header_frame, text=f"📁 {gender_display(gender)}",
                     font=CTkFont(size=14, weight="bold")).pack(side="left")
        if stats["timestamp"]:
            ctk.CTkLabel(header_frame, text=f"Stand: {stats['timestamp']}",
                         font=CTkFont(size=10), text_color=("gray40", "gray60")).pack(side="right")
        ctk.CTkLabel(gender_frame,
                     text=f"Neu: {stats['new']}  ·  Abgeholt: {stats['happy']}  ·  "
                          f"Geblieben: {stats['stayed']}",
                     font=CTkFont(size=12)).pack(padx=10, pady=5, anchor="w")

    ctk.CTkButton(stats_window, text="🔄 Aktualisieren",
                  command=lambda: (stats_window.destroy(), show_statistics_dashboard(root))).pack(pady=(10, 0))
    ctk.CTkButton(stats_window, text="Schließen", command=stats_window.destroy,
                  fg_color=("gray70", "gray30"), hover_color=("gray60", "gray40")).pack(pady=(6, 12))

    stats_window.after(50, stats_window.lift)


# --------------------------------------------------------------------------- #
# Main window
# --------------------------------------------------------------------------- #
def main():
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.title("Kesha Dog Manager")
    root.geometry("1000x820")
    root.minsize(900, 660)

    header_font = CTkFont(family="Arial", size=18, weight="bold")
    section_font = CTkFont(family="Arial", size=13, weight="bold")
    caption_font = CTkFont(family="Arial", size=11, weight="bold")
    mono_font = CTkFont(family="Consolas", size=13)
    ui_font = CTkFont(family="Arial", size=12)

    SIDEBAR_W = 210
    CAPTION_COLOR = ("gray40", "gray60")

    title = ctk.CTkLabel(root, text="🐾 Kesha Dog Manager", font=header_font)
    title.pack(pady=(10, 0))

    # --- Sidebar ---------------------------------------------------------- #
    left_frame = ctk.CTkFrame(root, fg_color="transparent")
    left_frame.pack(side="left", fill="y", padx=10, pady=10, anchor="n")

    # Search
    search_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
    ctk.CTkLabel(search_frame, text="🔍 Hund suchen", font=section_font).pack(
        side="top", anchor="w", pady=(0, 2))
    search_var = ctk.StringVar()
    search_row = ctk.CTkFrame(search_frame, fg_color="transparent")
    search_row.pack(side="top", anchor="w")
    search_entry = ctk.CTkEntry(search_row, textvariable=search_var, width=SIDEBAR_W - 40,
                                placeholder_text="Name eingeben …")
    search_entry.pack(side="left")
    btn_clear = ctk.CTkButton(search_row, text="✕", width=28,
                              fg_color=("gray70", "gray30"), hover_color=("gray60", "gray40"))
    btn_clear.pack(side="left", padx=(4, 0))
    search_frame.pack(side="top", pady=(0, 12), anchor="w")

    # Actions
    ctk.CTkLabel(left_frame, text="AKTIONEN", font=caption_font, text_color=CAPTION_COLOR).pack(
        side="top", anchor="w", pady=(0, 2))
    btn_check = ctk.CTkButton(left_frame, text="🔍 Änderungen prüfen", width=SIDEBAR_W, height=40)
    btn_check.pack(side="top", pady=3, anchor="w")
    btn_sync = ctk.CTkButton(left_frame, text="🐶 Wooff!", width=SIDEBAR_W, height=40,
                             fg_color=DANGER_FG, hover_color=DANGER_HOVER)
    btn_sync.pack(side="top", pady=3, anchor="w")

    # Views
    ctk.CTkLabel(left_frame, text="ANSICHTEN", font=caption_font, text_color=CAPTION_COLOR).pack(
        side="top", anchor="w", pady=(12, 2))
    category_var = ctk.StringVar(value=ALL_LABEL)
    DISPLAY_TO_GENDER = {gender_display(g): g for g in dogsGender}
    category_menu = ctk.CTkOptionMenu(
        left_frame, width=SIDEBAR_W, variable=category_var,
        values=[ALL_LABEL] + [gender_display(g) for g in dogsGender])
    category_menu.pack(side="top", pady=(0, 4), anchor="w")
    btn_new = ctk.CTkButton(left_frame, text="🆕 Neue Hunde", width=SIDEBAR_W)
    btn_new.pack(side="top", pady=3, anchor="w")
    btn_happy = ctk.CTkButton(left_frame, text="🎊 Abgeholt", width=SIDEBAR_W)
    btn_happy.pack(side="top", pady=3, anchor="w")
    btn_stayed = ctk.CTkButton(left_frame, text="🏠 Geblieben", width=SIDEBAR_W)
    btn_stayed.pack(side="top", pady=3, anchor="w")
    btn_changed = ctk.CTkButton(left_frame, text="📝 Geänderte", width=SIDEBAR_W)
    btn_changed.pack(side="top", pady=3, anchor="w")
    btn_stats = ctk.CTkButton(left_frame, text="📊 Statistik", width=SIDEBAR_W)
    btn_stats.pack(side="top", pady=3, anchor="w")

    # Links
    ctk.CTkLabel(left_frame, text="LINKS", font=caption_font, text_color=CAPTION_COLOR).pack(
        side="top", anchor="w", pady=(12, 2))
    btn_quoka = ctk.CTkButton(left_frame, text="Quoka", width=SIDEBAR_W,
                              fg_color=("gray70", "gray30"), hover_color=("gray60", "gray40"),
                              command=lambda: webbrowser.open("https://quoka.de"))
    btn_quoka.pack(side="top", pady=3, anchor="w")
    btn_kesha = ctk.CTkButton(left_frame, text="Kesha Website", width=SIDEBAR_W,
                              fg_color=("gray70", "gray30"), hover_color=("gray60", "gray40"),
                              command=lambda: webbrowser.open("https://tierschutzverein-kesha.de"))
    btn_kesha.pack(side="top", pady=3, anchor="w")

    # Progress (hidden until a run starts); kept as the last top-flow item so
    # showing/hiding it never reshuffles the buttons above it.
    progress_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
    progress_label = ctk.CTkLabel(progress_frame, text="0%", font=CTkFont(size=11))
    progress_label.pack(side="top", anchor="w")
    progress_bar = ctk.CTkProgressBar(progress_frame, width=SIDEBAR_W, mode="determinate")
    progress_bar.pack(side="top", pady=(2, 0))

    # Bottom of sidebar
    btn_exit = ctk.CTkButton(left_frame, text="❌ Beenden", width=SIDEBAR_W,
                             fg_color=("gray70", "gray30"), hover_color=("gray60", "gray40"))
    btn_exit.pack(side="bottom", pady=(8, 0), anchor="w")
    shortcuts_text = ("⌨️  F5 Prüfen · Strg+N Neue · Strg+H Abgeholt\n"
                      "Strg+G Geblieben · Strg+E Geänderte\n"
                      "Strg+T Statistik · Strg+F Suche · Esc leeren")
    ctk.CTkLabel(left_frame, text=shortcuts_text, font=CTkFont(family="Arial", size=10),
                 justify="left", text_color=CAPTION_COLOR).pack(side="bottom", pady=(10, 4), anchor="w")

    # --- Output area ------------------------------------------------------ #
    status_var = ctk.StringVar()
    status_bar = ctk.CTkLabel(root, textvariable=status_var, anchor="w", font=ui_font)
    status_bar.pack(fill="x", side="bottom", ipady=2)  # packed before output (correct pack order)

    output_frame = ctk.CTkFrame(root, fg_color="transparent")
    output_frame.pack(padx=10, pady=10, fill="both", expand=True)
    output = CTkTextbox(output_frame, font=mono_font, wrap="word")
    output.pack(fill="both", expand=True)
    output.configure(state="disabled")
    _configure_output_tags(output)

    # --- State & orchestration ------------------------------------------- #
    # processing = the scan/apply run is active; every control is locked.
    # bg         = the dogwatch change check runs in the background; only the
    #              two buttons that could collide with it are locked.
    state = {"processing": False, "bg": False, "view": None}
    all_controls = [btn_check, btn_sync, btn_new, btn_happy, btn_stayed, btn_changed,
                    btn_stats, btn_quoka, btn_kesha, category_menu, btn_clear,
                    btn_exit, search_entry]
    bg_locked_controls = [btn_check, btn_sync]

    def set_busy(busy):
        state["processing"] = busy
        set_buttons_state(all_controls, ctk.DISABLED if busy else ctk.NORMAL)

    def set_bg(active):
        state["bg"] = active
        set_buttons_state(bg_locked_controls, ctk.DISABLED if active else ctk.NORMAL)

    def show_progress():
        _set_progress(progress_bar, progress_label, 0)
        progress_frame.pack(side="top", pady=(10, 0), anchor="w")

    def hide_progress():
        progress_frame.pack_forget()

    def clear_output():
        output.configure(state="normal")
        output.delete(1.0, ctk.END)
        output.configure(state="disabled")

    def log(msg):
        root.after(0, lambda: _append_output(output, msg))

    def set_fraction(fraction):
        root.after(0, lambda: _set_progress(progress_bar, progress_label, fraction))

    def scan_async(on_done):
        def worker():
            try:
                plans = scan_all(log, set_fraction)
            except Exception as e:
                plans = None
                root.after(0, lambda: _append_output(output, f"\n[FEHLER] {e}\n"))
            root.after(0, lambda: on_done(plans))
        threading.Thread(target=worker, daemon=True).start()

    # --- Background change check (dogwatch) ------------------------------ #
    def on_change_progress(done, total):
        def update():
            _set_progress(progress_bar, progress_label, (done / total) if total else 1.0)
            set_status(status_var,
                       f"Prüfe Beschreibung, Preis & Fotos bestehender Hunde … {done}/{total}")
        root.after(0, update)

    def finish_changes(summary, error=None):
        hide_progress()
        set_bg(False)
        if error:
            set_status(status_var, f"Änderungsprüfung abgebrochen: {error}")
            return
        n = summary.n_changed
        msg = (f"Änderungsprüfung fertig: {n} Hund(e) mit Änderungen – siehe „📝 Geänderte“."
               if n else "Änderungsprüfung fertig: keine Änderungen an bestehenden Hunden.")
        if summary.errors:
            msg += f" · {len(summary.errors)} Seite(n) nicht prüfbar"
        if summary.warnings:
            msg += f" · {len(summary.warnings)} Warnung(en)"
        set_status(status_var, msg + f" ({summary.seconds:.0f} s)")
        btn_changed.configure(text=f"📝 Geänderte ({n})" if n else "📝 Geänderte")
        if state["view"] is show_changed_dogs:
            refresh_view()

    def start_change_pipeline(plans):
        """Run dogwatch on a daemon thread; the GUI stays responsive."""
        if state["bg"]:
            return
        set_bg(True)
        show_progress()
        set_status(status_var, "Prüfe Beschreibung, Preis & Fotos bestehender Hunde …")

        def worker():
            try:
                summary = run_dogwatch(plans, dogs_path=DOGS_PATH,
                                       report_path=report_module.REPORT_PATH,
                                       reist_bald=REIST_BALD, on_progress=on_change_progress)
            except Exception as e:
                msg = str(e)
                root.after(0, lambda: finish_changes(None, msg))
                return
            root.after(0, lambda: finish_changes(summary))

        threading.Thread(target=worker, daemon=True).start()

    # --- Scan / apply ------------------------------------------------------ #
    def do_check():
        if state["processing"] or state["bg"]:
            return
        set_busy(True)
        clear_output()
        _append_output(output, "[Prüfe Änderungen … es wird nichts geändert]\n")
        show_progress()

        def after(plans):
            hide_progress()
            set_busy(False)
            if plans is None:
                set_status(status_var, "Abruf fehlgeschlagen.")
                return
            _render_preview(output, plans)
            _, n_new, n_del, n_block, n_err = summarize_plans(plans)
            msg = f"Prüfung: +{n_new} neu, −{n_del} abgeholt"
            if n_block:
                msg += f", {n_block} gesperrt"
            if n_err:
                msg += f", {n_err} Fehler"
            set_status(status_var, msg)

        scan_async(after)

    def finish_apply(summary, plans):
        hide_progress()
        set_busy(False)
        output.configure(state="normal")
        output.delete(1.0, ctk.END)
        _configure_output_tags(output)
        if summary is not None:
            output.insert(ctk.END, "Zusammenfassung\n", "header")
            output.insert(ctk.END, _summary_line(summary) + "\n\n", "stats")
            set_status(status_var, _summary_line(summary))
        else:
            output.insert(ctk.END, "Mit Fehler beendet.\n\n", "gone")
            set_status(status_var, "Mit Fehler beendet.")
        for gender in dogsGender:
            output.insert(ctk.END, get_report_string(gender), "header")
            output.insert(ctk.END, "\n" + ("=" * 60) + "\n\n", "section")
        output.see(1.0)
        output.configure(state="disabled")
        # Scan/apply is done and the UI is unlocked again -> start the change check.
        if summary is not None:
            start_change_pipeline(plans)

    def run_apply(plans):
        set_busy(True)
        clear_output()
        _append_output(output, "[Aktualisiere …]\n")
        show_progress()
        set_fraction(SCAN_WEIGHT)

        def worker():
            summary = None
            try:
                summary = apply_all(plans, log, set_fraction)
            except Exception as e:
                root.after(0, lambda: _append_output(output, f"\n[FEHLER] {e}\n"))
            root.after(0, lambda: finish_apply(summary, plans))

        threading.Thread(target=worker, daemon=True).start()

    def do_sync():
        if state["processing"] or state["bg"]:
            return
        set_busy(True)
        clear_output()
        _append_output(output, "[Prüfe Änderungen …]\n")
        show_progress()

        def after(plans):
            hide_progress()
            if plans is None:
                set_busy(False)
                set_status(status_var, "Abruf fehlgeschlagen.")
                return
            lines, n_new, n_del, n_block, n_err = summarize_plans(plans)
            if n_new == 0 and n_del == 0 and n_block == 0:
                # Nothing to create/delete: go straight to the change check.
                set_busy(False)
                _render_preview(output, plans)
                set_status(status_var, "Keine neuen/abgeholten Hunde.")
                start_change_pipeline(plans)
                return
            # Deletions require explicit confirmation; pure creations proceed directly.
            if n_del > 0:
                set_busy(False)  # let the modal be interactive
                if not confirm_apply(root, lines, n_new, n_del, n_block, n_err):
                    _render_preview(output, plans)
                    set_status(status_var, "Abgebrochen – nichts geändert.")
                    return
            run_apply(plans)

        scan_async(after)

    def current_filter():
        v = category_var.get()
        return "ALL" if v == ALL_LABEL else DISPLAY_TO_GENDER.get(v, "ALL")

    def run_view(fn):
        if state["processing"]:
            return
        state["view"] = fn
        fn(output, status_var, search_var.get(), current_filter())

    def refresh_view():
        if state["processing"] or state["view"] is None:
            return
        state["view"](output, status_var, search_var.get(), current_filter())

    def on_search_enter():
        run_view(state["view"] or show_new_dogs)

    def guarded_stats():
        if state["processing"]:
            return
        show_statistics_dashboard(root)

    def on_close():
        if state["processing"]:
            messagebox.showwarning(
                "Bitte warten",
                "Ein Vorgang läuft noch. Bitte warten, bis er abgeschlossen ist.")
            return
        # The background change check may still be running: it is a daemon
        # thread and dogwatch only writes its own database and a report section
        # (atomically), so closing is safe; it simply runs again next time.
        root.destroy()

    # --- Wire up ---------------------------------------------------------- #
    btn_check.configure(command=do_check)
    btn_sync.configure(command=do_sync)
    btn_new.configure(command=lambda: run_view(show_new_dogs))
    btn_happy.configure(command=lambda: run_view(show_gone_dogs))
    btn_stayed.configure(command=lambda: run_view(show_stayed_dogs))
    btn_changed.configure(command=lambda: run_view(show_changed_dogs))
    btn_stats.configure(command=guarded_stats)
    btn_exit.configure(command=on_close)
    btn_clear.configure(command=lambda: (search_var.set(""), refresh_view()))
    category_menu.configure(command=lambda _choice: refresh_view())
    search_entry.bind("<Return>", lambda e: on_search_enter())

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.bind("<Control-n>", lambda e: run_view(show_new_dogs))
    root.bind("<Control-h>", lambda e: run_view(show_gone_dogs))
    root.bind("<Control-g>", lambda e: run_view(show_stayed_dogs))
    root.bind("<Control-e>", lambda e: run_view(show_changed_dogs))
    root.bind("<F5>", lambda e: do_check())
    root.bind("<Control-t>", lambda e: guarded_stats())
    root.bind("<Control-f>", lambda e: search_entry.focus())
    root.bind("<Escape>", lambda e: (search_var.set(""), refresh_view()))
    root.bind("<Control-w>", lambda e: on_close())

    set_status(status_var, "Bereit. „🔍 Änderungen prüfen“ zeigt gefahrlos, was neu ist.")
    search_entry.focus()
    root.mainloop()


if __name__ == "__main__":
    main()

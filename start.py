#!/usr/bin/python
from source.doglist import Doglist
from source.manage_folder import create_new_dogs, delete_dog
from source.report import create_report, show_report
from source.global_defines import gender_display
from source.cli import CLI, EXIT

dogsGender = ["Hündinen", "Rüden", "Welpen_Madchen", "Welpen_und_Junghunde", "Pflegestelle"]

# Map menu key -> category. A dict lookup (not list index arithmetic) means a
# stray "0" or negative number can never resolve to the wrong category.
MENU = {str(i): gender for i, gender in enumerate(dogsGender, start=1)}


def _confirm(prompt):
    """Yes/No prompt defaulting to No; treats Ctrl+C / EOF as No."""
    try:
        return input(prompt).strip().lower() in ("j", "ja", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def process_gender(gender):
    """Refresh one category: report, create new dogs, delete adopted (confirmed)."""
    print(f"\n=== {gender_display(gender)} ===")
    try:
        dog_list = Doglist(gender)
    except Exception as e:
        print(f"[FEHLER] Abruf für {gender_display(gender)} fehlgeschlagen: {e}. Übersprungen.")
        return

    create_report(dog_list, gender)

    print("Neue Hunde werden erstellt ...")
    created, failed, no_images = create_new_dogs(gender, dog_list.pets)

    happy = dog_list.happy_dogs()
    deleted = 0
    if happy:
        print(f"\n{len(happy)} Ordner als abgeholt erkannt: {', '.join(happy)}")
        if _confirm(f"Diese {len(happy)} Ordner löschen? [j/N]: "):
            for dog in happy:
                if delete_dog(gender, dog):
                    deleted += 1
        else:
            print("Löschen übersprungen.")

    print(f"Fertig: {created} erstellt, {deleted} gelöscht, "
          f"{failed} fehlgeschlagen, {no_images} ohne Bilder.")
    show_report(gender)


def start():
    """Interactive menu loop. Never crashes on bad input; Ctrl+C/EOF exits cleanly."""
    cli = CLI()
    while True:
        cli.create_menu()
        try:
            choice = input("Kategorie wählen (1-6, E=Ende): ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\nBeendet.")
            return

        if choice == EXIT:
            print("Auf Wiedersehen!")
            return
        elif choice in MENU:
            process_gender(MENU[choice])
        elif choice in ("6", "ALL", "ALLE"):
            for gender in dogsGender:
                process_gender(gender)
        else:
            print("Ungültige Eingabe. Bitte 1-6 oder E wählen.")


if __name__ == "__main__":
    start()

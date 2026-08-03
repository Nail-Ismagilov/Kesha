import os
_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
REPORT_PATH = os.path.join(_PROJECT_ROOT, "report")
DOGS_PATH = os.path.join(_PROJECT_ROOT, "hunde")
# Anchor the description template to the project, not the current working dir,
# so the app works regardless of where it is launched from.
MAKET_PATH = os.path.join(_PROJECT_ROOT, "Maket.txt")

# The internal category keys double as folder names and URL keys, so they must
# stay exactly as-is. These are the human-friendly, correctly-spelled labels to
# show users instead of the raw keys (e.g. "Welpen_und_Junghunde").
GENDER_DISPLAY = {
    "Hündinen": "Hündinnen",
    "Rüden": "Rüden",
    "Welpen_Madchen": "Welpen (Mädchen)",
    "Welpen_und_Junghunde": "Welpen & Junghunde",
    "Pflegestelle": "Pflegestelle",
}


def gender_display(gender):
    """Human-friendly label for a category key (falls back to the key)."""
    return GENDER_DISPLAY.get(gender, gender)

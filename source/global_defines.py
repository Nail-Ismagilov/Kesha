import os
_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
REPORT_PATH = os.path.join(_PROJECT_ROOT, "report")
DOGS_PATH = os.path.join(_PROJECT_ROOT, "hunde")
# Anchor the description template to the project, not the current working dir,
# so the app works regardless of where it is launched from.
MAKET_PATH = os.path.join(_PROJECT_ROOT, "Maket.txt")

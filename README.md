# Kesha Dog Manager

This application helps manage dog reports and lists for the Kesha animal welfare organization, now with a modern, user-friendly interface using [customtkinter](https://customtkinter.tomschimansky.com/).

## Features
- Modern GUI with sidebar navigation
- View, process, and generate dog reports
- Clickable dog names open their folders
- Dark mode and theming support
- Emoji and improved visual feedback

## Requirements
- Python 3.7+
- See `requirements.txt` for dependencies (including `customtkinter`)

## Installation
1. Clone the repository or download the source code.
2. (Recommended) Create and activate a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On macOS/Linux
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage
Run the GUI with:
```
python gui.py
```

## Notes
- The GUI now uses `customtkinter` for a modern look and feel.
- All previous features are preserved, with improved usability and appearance.
- If you encounter issues, ensure you have installed all dependencies from `requirements.txt`.

## Recent Improvements
- **Performance:** Reduced redundant file operations and improved efficiency in file/image handling.
- **Modularity:** Centralized folder creation and error handling; split large functions for maintainability.
- **Robustness:** All file and report operations now ensure directories exist before writing.

## Project Structure
```
Kesha/
  start.py
  source/
    cli.py
    doglist.py
    dogs.py
    dogs_from_PC.py
    dogs_from_url.py
    elements_from_url.py
    global_defines.py
    manage_folder.py
    report.py
  Maket.txt
```

## Credits
- Developed by [Your Name/Team]

## License
[Specify your license here] 
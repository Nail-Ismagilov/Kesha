# Kesha Dog Manager

This application helps manage dog reports and lists for the Kesha animal welfare organization, now with a modern, user-friendly interface using [customtkinter](https://customtkinter.tomschimansky.com/).

## Features
- Modern GUI with sidebar navigation
- View, process, and generate dog reports
- Clickable dog names open their folders
- Dark mode and theming support
- Emoji and improved visual feedback
- Improved readability with white text and light tag colors for all output
- **Change detection (dogwatch):** after every "Wooff!" run, existing dogs are checked for description, Schutzgebühr (price), first-photo and photo-count changes; results appear in the new "📝 Geänderte" view and in the `GEÄNDERT:` section of each category report.

## Requirements
- Python 3.7+
- See `requirements.txt` for dependencies (including `customtkinter`, `pillow`)

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

### Change detection (dogwatch)

After "Wooff!" the app automatically checks all online dogs (description, price, first photo, photo count) in the background. Results show up in:
- the **📝 Geänderte** view (Strg+E) in the GUI;
- the `GEÄNDERT:` section at the bottom of each `*_report.txt`.

You can also check a single dog from the command line:
```
python -m dogwatch check https://tierschutzverein-kesha.de/nera/ --db test.db
```

With the local folder (enables photo checks):
```
python -m dogwatch check https://tierschutzverein-kesha.de/nera/ --db test.db --folder "C:\path\to\dogs\Rüden\nera" --name nera
```

Or check many dogs at once from a JSON file:
```
python -m dogwatch run --dogs dogs.json --db dogwatch.db
```

`dogs.json` format:
```json
[{"key": "Rüden/benny", "name": "benny", "url": "https://...", "folder": "C:/dogs/Rüden/benny"}]
```

## Testing

Run the offline test suite:
```
python -m pytest tests/ -v
```

## Notes
- The GUI now uses `customtkinter` for a modern look and feel.
- All previous features are preserved, with improved usability and appearance.
- Output text is white (with light tag colors) for better readability, especially in dark mode.
- If you encounter issues, ensure you have installed all dependencies from `requirements.txt`.
- The change check only reads dog folders; it writes `dogwatch.db` and the `GEÄNDERT:` report section, both next to the existing reports.
- First run only builds baselines (no "changed" messages); the same change is reported once.

## Project Structure
```
Kesha/
  start.py
  gui.py
  dogwatch/
    __init__.py
    __main__.py
    checks/
      description.py
      first_photo.py
      photo_count.py
    context.py
    http.py
    imagecmp.py
    models.py
    page.py
    runner.py
    store.py
  source/
    cli.py
    doglist.py
    dogs.py
    dogs_from_PC.py
    dogs_from_url.py
    dogwatch_adapter.py
    elements_from_url.py
    global_defines.py
    manage_folder.py
    report.py
  tests/
    test_step1.py
    test_step2.py
    test_step3.py
    test_step4.py
    test_step5.py
  requirements.txt
  Maket.txt
```

## Credits
- Developed by [Nail Ismagilov]

## License
[] 
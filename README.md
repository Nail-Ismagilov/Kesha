# Kesha Project

## Overview
Kesha is a Python-based tool for managing and reporting on dog data, including downloading images and generating reports. It is designed for modularity, performance, and ease of use.

## Features
- Download and organize dog data from URLs
- Generate and manage reports by gender
- Automatic folder creation for all file operations
- Modular, maintainable codebase
- Error handling for file and network operations

## Installation
1. Clone the repository:
   ```sh
   git clone <your-repo-url>
   cd Kesha
   ```
2. Create and activate a Python virtual environment:
   ```sh
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Ensure you have Python 3.7+ installed.
4. Install required packages:
   ```sh
   pip install -r requirements.txt
   ```
   *(Create requirements.txt if needed, e.g., for requests, beautifulsoup4)*

## Usage
- Run the main script:
  ```sh
  python start.py
  ```
- The scripts in `source/` provide CLI and programmatic access to dog data management and reporting.

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
# notecli

A simple CLI for quick notes with the ability to duplicate entries into the macOS Notes app.

## Features

- Add text notes with an optional title and body.
- List all saved notes (shows the first 8 characters of the ID).
- Remove a note by ID.
- `--to-notes` option simultaneously creates a note in the Notes app (iCloud or On My Mac, depending on your script settings).

## Installation

1. Clone the repository (or just copy the `notecli.py` file):
   ```bash
   git clone <repo-url> notecli
   cd notecli
   ```
2. (Optional) Install dependencies – currently the `requirements.txt` file is empty, no external packages are required:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
3. Make the script executable:
   ```bash
   chmod +x notecli.py
   ```
4. (For macOS) Grant automation permission to the Notes app:
   - Open **System Settings → Privacy & Security → Automation**.
   - Find your terminal (e.g., Terminal or iTerm2) and enable access to **Notes**.

## Usage

```bash
# Add a note (locally only)
./notecli.py add -t "Title" -b "Note text"

# Add a note and duplicate it in the Notes app
./notecli.py add -t "Title" -b "Note text" --to-notes

# List all notes
./notecli.py list

# Remove a note (the first 8 characters of the ID are sufficient)
./notecli.py rm <ID>
```

## Data Storage

Notes are saved in a local JSON file:
```
~/.notecli_data.json
```
It is a simple array of objects:
```json
[
  {"id": "uuid", "title": "...", "body": "..."},
  ...
]
```

## License

MIT – feel free to copy and modify.

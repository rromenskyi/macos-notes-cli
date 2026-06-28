# notecli

A simple CLI for quick notes with the ability to duplicate entries into the macOS Notes app.

## Features

- Add text notes with an optional title and body.
- List local notecli notes or read directly from macOS Notes.
- Import existing macOS Notes into the local notecli index.
- Remove a note by ID.
- Beautify a note through a local OpenAI-compatible LLM endpoint.
- New notes are also created in the macOS Notes app by default.
- Notes created by `notecli` store their macOS Notes ID, so `rm` deletes the linked system note and `bfy` updates it.

## Installation

1. Clone the repository (or just copy the `notecli.py` file):
   ```bash
   git clone <repo-url> notecli
   cd notecli
   ```
2. Install dependencies:
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
# Add a note locally and in the macOS Notes app
./notecli.py add -t "Title" -b "Note text"

# Add a note locally only
./notecli.py add -t "Title" -b "Note text" --local-only

# List all notes
./notecli.py list

# List notes directly from macOS Notes
./notecli.py list --system

# Import existing macOS Notes into notecli
./notecli.py sync

# Remove a note (the first 8 characters of the ID are sufficient)
./notecli.py rm <ID>

# Beautify a note using the configured local LLM endpoint
./notecli.py bfy <ID>
```

## Data Storage

Notes are saved in a local JSON file:
```
~/.notecli_data.json
```
It is a simple array of objects. Notes synced to macOS include `metadata.macos_note_id`:
```json
[
  {"id": "uuid", "title": "...", "body": "...", "metadata": {"macos_note_id": "..."}},
  ...
]
```

## License

MIT – feel free to copy and modify.

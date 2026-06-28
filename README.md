# notecli

`notecli` is a small macOS-first command line tool for capturing notes quickly, keeping a local JSON index, and linking those notes to Apple Notes.

It is built for a simple workflow: add a note from the terminal, have it appear in Notes.app, then use the CLI to list, import, delete, or clean it up with a local OpenAI-compatible LLM.

## Features

- Add notes with a title and body from the terminal.
- Add and immediately beautify a note with `addb`.
- Create new notes in macOS Notes by default.
- Keep a local index in `~/.notecli_data.json`.
- Store the linked macOS Notes ID for synced notes.
- List local notes or read directly from Notes.app.
- Show a full local note by ID prefix.
- Import existing Notes.app notes into the local index.
- Delete linked system notes with `rm`.
- Beautify note titles and bodies through a local OpenAI-compatible chat endpoint such as LM Studio.
- Use `--local-only` when you do not want to create a system note.

## Requirements

- macOS with the Notes app.
- Python 3.9 or newer.
- Apple automation permission for your terminal.
- Optional: a local OpenAI-compatible LLM server for `bfy`.

## Installation

```bash
git clone https://github.com/rromenskyi/macos-notes-cli.git
cd macos-notes-cli
./install.sh
```

The installer creates a local virtual environment in `.venv`, installs dependencies from `requirements.txt`, and writes a launcher to `~/.local/bin/notecli`.

If `notecli` is not found after installation, add `~/.local/bin` to your shell `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Grant Notes automation permission when macOS asks for it. You can also check it manually in:

```text
System Settings -> Privacy & Security -> Automation
```

Enable access from your terminal app to Notes.

## Usage

Add a note. By default this writes to the local index and creates a linked note in macOS Notes:

```bash
notecli add -t "Incident follow-up" -b "Check Grafana alerts after deploy"
```

You can also write a note as one quoted argument separated by `;`:

```bash
notecli add "Incident follow-up; Check Grafana alerts after deploy"
```

Add a local-only note:

```bash
notecli add -t "Draft" -b "Temporary note" --local-only
```

Open your editor instead of passing the note text as command arguments:

```bash
notecli add --edit
```

Add a note and immediately beautify it with the configured LLM:

```bash
notecli addb -t "Raw idea" -b "need clean this up later"
```

The same shorthand works with `addb`:

```bash
notecli addb "shopping list; milk meat breakfast sausages"
```

List local notes:

```bash
notecli list
```

Show a full local note:

```bash
notecli show <ID>
```

List notes directly from macOS Notes without importing them:

```bash
notecli list --system
```

Import existing macOS Notes into the local index:

```bash
notecli sync
```

Delete a note by ID prefix:

```bash
notecli rm <ID>
```

Beautify a note title and body with the configured LLM:

```bash
notecli bfy <ID>
```

For development, you can still run the script directly:

```bash
./notecli.py list
```

## LLM Configuration

`bfy` reads optional settings from:

```text
~/.notecli_config.json
```

Example:

```json
{
  "llm_api_url": "http://localhost:1234/v1/chat/completions",
  "llm_model": "google/gemma-4-26b-a4b-qat",
  "llm_timeout": 120
}
```

The endpoint should behave like OpenAI's chat completions API.

If this file is missing, `bfy` and `addb` do not try to guess defaults. They print the required config shape and exit without waiting on a network timeout. Increase `llm_timeout` if your local model needs more time to load on the first request.

`notecli` also sends provider-specific flags to disable reasoning where supported. If you still need to cap output size, add an optional `llm_max_tokens` value to the config.

## Data Model

Local notes are stored in:

```text
~/.notecli_data.json
```

Synced notes include the macOS Notes identifier in `metadata.macos_note_id`:

```json
[
  {
    "id": "uuid",
    "title": "Incident follow-up",
    "body": "Check Grafana alerts after deploy",
    "metadata": {
      "macos_note_id": "x-coredata://..."
    }
  }
]
```

Notes imported with `sync` get a local UUID and keep their system note ID, so later `rm` and `bfy` can target the linked Notes.app item.

## Sync Behavior

`notecli` is not a background sync daemon. It performs explicit operations:

- `add` creates a local record and a system note.
- `addb` creates a note, beautifies it, and updates the linked system note.
- `list` reads the local index.
- `show` prints the full local note body and metadata.
- `list --system` reads Notes.app directly.
- `sync` imports Notes.app notes that are not already in the local index.
- `rm` removes the local record and, when linked, deletes the system note.
- `bfy` updates the local body and, when linked, updates the system note.

## License

MIT

import subprocess
import sys
import re
import html
from typing import Optional

NOTE_FIELD_SEPARATOR = "\x1f"
NOTE_RECORD_SEPARATOR = "\x1e"


def create_macos_note(title: str, body: str) -> Optional[str]:
    """
    Create a note in macOS Notes and return its stable Notes ID.
    Content is passed through argv, so it is not interpolated into the script.
    """
    applescript = '''
    on run argv
        set theTitle to item 1 of argv
        set theBody to item 2 of argv
        tell application "Notes"
            set targetFolder to folder "Notes" of account "iCloud"
            set newNote to make new note at targetFolder with properties {name: theTitle, body: theBody}
            return id of newNote
        end tell
    end run
    '''
    try:
        result = subprocess.run(
            ["osascript", "-", title, markdown_to_notes_html(body)],
            input=applescript,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(
            f"[WARN] Failed to create note in Notes app: {e.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    except FileNotFoundError:
        print(
            "[WARN] 'osascript' not found. Are you on macOS?",
            file=sys.stderr,
        )
        return None


def update_macos_note(note_id: str, title: str, body: str) -> bool:
    applescript = '''
    on run argv
        set noteId to item 1 of argv
        set theTitle to item 2 of argv
        set theBody to item 3 of argv
        tell application "Notes"
            set targetNote to note id noteId
            set name of targetNote to theTitle
            set body of targetNote to theBody
        end tell
    end run
    '''
    return _run_note_script(applescript, [note_id, title, markdown_to_notes_html(body)], "update")


def get_macos_note(note_id: str) -> Optional[dict]:
    applescript = '''
    on run argv
        set noteId to item 1 of argv
        set fieldSeparator to ASCII character 31
        tell application "Notes"
            set targetNote to note id noteId
            return (id of targetNote) & fieldSeparator & (name of targetNote) & fieldSeparator & (body of targetNote)
        end tell
    end run
    '''
    try:
        result = subprocess.run(
            ["osascript", "-", note_id],
            input=applescript,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(
            f"[WARN] Failed to read note in Notes app: {e.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    except FileNotFoundError:
        print(
            "[WARN] 'osascript' not found. Are you on macOS?",
            file=sys.stderr,
        )
        return None

    parts = result.stdout.strip().split(NOTE_FIELD_SEPARATOR, 2)
    if len(parts) != 3:
        return None
    note_id, title, body = parts
    return {"id": note_id, "title": title, "body": body}


def delete_macos_note(note_id: str) -> bool:
    applescript = '''
    on run argv
        set noteId to item 1 of argv
        tell application "Notes"
            delete note id noteId
        end tell
    end run
    '''
    return _run_note_script(applescript, [note_id], "delete")


def list_macos_notes() -> list[dict]:
    applescript = f'''
    on run argv
        set fieldSeparator to ASCII character 31
        set recordSeparator to ASCII character 30
        set output to {{}}
        tell application "Notes"
            set targetFolder to folder "Notes" of account "iCloud"
            repeat with theNote in notes of targetFolder
                set noteId to id of theNote
                set noteName to name of theNote
                set noteBody to body of theNote
                set end of output to noteId & fieldSeparator & noteName & fieldSeparator & noteBody
            end repeat
        end tell
        set AppleScript's text item delimiters to recordSeparator
        set renderedOutput to output as text
        set AppleScript's text item delimiters to ""
        return renderedOutput
    end run
    '''
    try:
        result = subprocess.run(
            ["osascript", "-"],
            input=applescript,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(
            f"[WARN] Failed to list notes in Notes app: {e.stderr.strip()}",
            file=sys.stderr,
        )
        return []
    except FileNotFoundError:
        print(
            "[WARN] 'osascript' not found. Are you on macOS?",
            file=sys.stderr,
        )
        return []

    rendered = result.stdout.strip()
    if not rendered:
        return []

    notes = []
    for record in rendered.split(NOTE_RECORD_SEPARATOR):
        parts = record.split(NOTE_FIELD_SEPARATOR, 2)
        if len(parts) != 3:
            continue
        note_id, title, body = parts
        notes.append({"id": note_id, "title": title, "body": body})
    return notes


def normalize_notes_body(body: str, title: str = "") -> str:
    text = html.unescape(body)
    text = re.sub(r"(?is)<li[^>]*>", "\n- ", text)
    text = re.sub(r"(?is)</li\s*>", "", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p\s*>", "\n", text)
    text = re.sub(r"(?is)</div\s*>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    lines = [line.strip() for line in text.splitlines()]
    normalized_lines = [line for line in lines if line]
    if title and normalized_lines and normalized_lines[0] == title.strip():
        normalized_lines = normalized_lines[1:]
    return "\n".join(normalized_lines).strip()


def markdown_to_notes_html(body: str) -> str:
    lines = body.splitlines()
    blocks = []
    paragraph = []
    list_items = []

    def flush_paragraph():
        if paragraph:
            escaped = "<br>".join(html.escape(line) for line in paragraph)
            blocks.append(f"<p>{escaped}</p>")
            paragraph.clear()

    def flush_list():
        if list_items:
            items = "".join(f"<li>{html.escape(item)}</li>" for item in list_items)
            blocks.append(f"<ul>{items}</ul>")
            list_items.clear()

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_list()
            continue

        bullet_match = re.match(r"^[-*]\s+(.+)$", stripped)
        numbered_match = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if bullet_match or numbered_match:
            flush_paragraph()
            list_items.append((bullet_match or numbered_match).group(1).strip())
            continue

        flush_list()
        paragraph.append(stripped)

    flush_paragraph()
    flush_list()

    if not blocks:
        return ""
    return "".join(blocks)


def _run_note_script(applescript: str, args: list[str], action: str) -> bool:
    try:
        subprocess.run(
            ["osascript", "-", *args],
            input=applescript,
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(
            f"[WARN] Failed to {action} note in Notes app: {e.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    except FileNotFoundError:
        print(
            "[WARN] 'osascript' not found. Are you on macOS?",
            file=sys.stderr,
        )
        return False

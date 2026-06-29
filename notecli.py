#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from notecli.core.models import Note
from notecli.core.storage import load_data, find_note_by_id_prefix_or_exact, update_data
from notecli.core.macos import (
    create_macos_note,
    delete_macos_note,
    get_macos_note,
    list_macos_notes,
    normalize_notes_body,
    update_macos_note,
)

CONFIG_FILE = Path.home() / ".notecli_config.json"

def load_config() -> dict:
    if CONFIG_FILE.is_file():
        try:
            import json
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def print_llm_config_help() -> None:
    print(
        "LLM is not configured. Create ~/.notecli_config.json, for example:\n"
        '{\n'
        '  "llm_api_url": "http://localhost:1234/v1/chat/completions",\n'
        '  "llm_model": "google/gemma-4-26b-a4b-qat",\n'
        '  "llm_timeout": 120\n'
        '}\n',
        file=sys.stderr,
    )

def load_llm_config() -> Optional[dict]:
    config = load_config()
    api_url = config.get("llm_api_url")
    model_name = config.get("llm_model")
    if not api_url or not model_name:
        print_llm_config_help()
        return None
    llm_config = {
        "api_url": api_url,
        "model_name": model_name,
        "timeout": int(config.get("llm_timeout", 120)),
    }
    if config.get("llm_max_tokens"):
        llm_config["max_tokens"] = int(config["llm_max_tokens"])
    return llm_config

def resolve_note_input(args) -> tuple[str, str]:
    positional_title, positional_body = parse_positional_note_text(args.text)
    title = args.title or positional_title
    body = args.body or positional_body
    return collect_note_input(title, body, args.edit)

def parse_positional_note_text(parts: list[str]) -> tuple[str, str]:
    if not parts:
        return "", ""

    raw = " ".join(parts).strip()
    if ";" in raw:
        title, body = raw.split(";", 1)
        return title.strip(), body.strip()

    title = parts[0].strip()
    body = " ".join(parts[1:]).strip()
    return title, body

def collect_note_input(title: str, body: str, edit: bool) -> tuple[str, str]:
    if edit:
        return collect_note_input_from_editor(title, body)

    if not title and not body and sys.stdin.isatty():
        title = input("Title: ").strip()
        print("Body. Finish with Ctrl-D:")
        body = sys.stdin.read().strip()

    return title, body

def collect_note_input_from_editor(title: str, body: str) -> tuple[str, str]:
    editor = os.environ.get("EDITOR", "nano")
    initial_content = f"{title}\n\n{body}".rstrip() + "\n"

    with tempfile.NamedTemporaryFile("w+", suffix=".md") as f:
        f.write(initial_content)
        f.flush()
        subprocess.run([editor, f.name], check=True)
        f.seek(0)
        content = f.read().strip("\n")

    if not content:
        return "", ""

    lines = content.splitlines()
    edited_title = lines[0].strip()
    edited_body = "\n".join(lines[1:]).strip()
    return edited_title, edited_body

def add_note(title: str, body: str, sync_to_notes: bool) -> tuple[str, bool]:
    note_id = str(uuid.uuid4())
    metadata = {}

    if sync_to_notes:
        macos_note_id = create_macos_note(title, body)
        if macos_note_id:
            metadata["macos_note_id"] = macos_note_id

    new_note = Note(id=note_id, title=title, body=body, metadata=metadata)

    def append_note(notes: list[Note]) -> list[Note]:
        notes.append(new_note)
        return notes

    update_data(append_note)

    return note_id, bool(metadata.get("macos_note_id"))

def list_notes(system: bool = False) -> None:
    if system:
        notes = list_macos_notes()
        if not notes:
            print("No notes found in Notes app.")
            return
        for n in notes:
            print(f"[system] {n['title'] or '(no title)'}")
        return

    notes = load_data()
    if not notes:
        print("No notes yet.")
        return
    for n in notes:
        print(f"[{n.id[:8]}] {n.title or '(no title)'}")

def show_note(note_id_prefix: str) -> bool:
    note = find_note_by_id_prefix_or_exact(note_id_prefix)
    if not note:
        return False

    print(f"ID: {note.id}")
    if note.metadata.get("macos_note_id"):
        print(f"macOS Notes ID: {note.metadata['macos_note_id']}")
    print(f"Title: {note.title or '(no title)'}")
    print()
    print(note.body)
    return True

def resolve_note_selector(note_id_or_selector: str) -> Optional[str]:
    if note_id_or_selector != "last":
        return note_id_or_selector

    notes = load_data()
    if not notes:
        return None
    return notes[-1].id

def sync_macos_notes() -> int:
    system_notes = list_macos_notes()
    if not system_notes:
        return 0

    imported_count = 0

    def import_notes(notes: list[Note]) -> list[Note]:
        nonlocal imported_count
        existing_macos_ids = {
            n.metadata.get("macos_note_id")
            for n in notes
            if n.metadata.get("macos_note_id")
        }

        for system_note in system_notes:
            macos_note_id = system_note["id"]
            if macos_note_id in existing_macos_ids:
                continue

            notes.append(
                Note(
                    id=str(uuid.uuid4()),
                    title=system_note["title"],
                    body=system_note["body"],
                    metadata={"macos_note_id": macos_note_id},
                )
            )
            existing_macos_ids.add(macos_note_id)
            imported_count += 1

        return notes

    update_data(import_notes)
    return imported_count

def remove_note(note_id_prefix: str) -> bool:
    matched = find_note_by_id_prefix_or_exact(note_id_prefix)
    if not matched:
        return False

    macos_note_id = matched.metadata.get("macos_note_id")
    if macos_note_id:
        delete_macos_note(macos_note_id)

    update_data(lambda notes: [n for n in notes if n.id != matched.id])
    return True

def improve_note_text(title: str, body: str) -> Optional[tuple[str, str]]:
    llm_config = load_llm_config()
    if not llm_config:
        return None

    from notecli.core.llm import beautify_note_content

    return beautify_note_content(
        title,
        body,
        llm_config["api_url"],
        llm_config["model_name"],
        llm_config["timeout"],
        llm_config.get("max_tokens"),
    )

def choose_conflict_source(local_note: Note, remote_note: dict) -> Optional[str]:
    print("Linked macOS note has changed outside notecli.", file=sys.stderr)
    print(f"Local title:  {local_note.title}", file=sys.stderr)
    print(f"Remote title: {remote_note['title']}", file=sys.stderr)

    if not sys.stdin.isatty():
        print("Run in an interactive terminal to choose local or remote changes.", file=sys.stderr)
        return None

    answer = input("Use remote Notes.app version before beautifying? [Y/n] ")
    if answer.strip().lower() in ("n", "no", "local", "l"):
        return "local"
    return "remote"

def macos_note_changed(local_note: Note, remote_note: dict) -> bool:
    return (
        local_note.title.strip() != remote_note["title"].strip()
        or normalize_notes_body(local_note.body) != normalize_notes_body(remote_note["body"])
    )

def beautify_note(note_id_prefix: str) -> bool:
    note = find_note_by_id_prefix_or_exact(note_id_prefix)
    if not note:
        return False

    macos_note_id = note.metadata.get("macos_note_id")
    if macos_note_id:
        remote_note = get_macos_note(macos_note_id)
        if remote_note and macos_note_changed(note, remote_note):
            source = choose_conflict_source(note, remote_note)
            if not source:
                print("Aborted. No changes were made.", file=sys.stderr)
                return False
            if source == "remote":
                note = Note(
                    id=note.id,
                    title=remote_note["title"],
                    body=normalize_notes_body(remote_note["body"]),
                    metadata=note.metadata,
                )
                update_data(
                    lambda notes: [
                        note if n.id == note.id else n
                        for n in notes
                    ]
                )

    improved_note = improve_note_text(note.title, note.body)
    
    if improved_note:
        new_title, new_body = improved_note
        if macos_note_id:
            update_macos_note(macos_note_id, new_title, new_body)

        update_data(
            lambda notes: [
                Note(id=n.id, title=new_title, body=new_body, metadata=n.metadata)
                if n.id == note.id
                else n
                for n in notes
            ]
        )
        return True
    return False

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="notecli", description="A simple CLI note-taking tool")
    sub = p.add_subparsers(dest="cmd", required=True)

    add_p = sub.add_parser("add", help="Add a new note")
    add_p.add_argument("text", nargs="*", help='Note text, e.g. "title; body"')
    add_p.add_argument("-t", "--title", default="", help="Note title")
    add_p.add_argument("-b", "--body", default="", help="Note body")
    add_p.add_argument("-e", "--edit", action="store_true", help="Open an editor to write the note")
    add_p.add_argument("--local-only", action="store_true", help="Do not sync to macOS Notes")
    add_p.add_argument("--to-notes", action="store_true", help=argparse.SUPPRESS)

    addb_p = sub.add_parser("addb", help="Add a new note and beautify it")
    addb_p.add_argument("text", nargs="*", help='Note text, e.g. "title; body"')
    addb_p.add_argument("-t", "--title", default="", help="Note title")
    addb_p.add_argument("-b", "--body", default="", help="Note body")
    addb_p.add_argument("-e", "--edit", action="store_true", help="Open an editor to write the note")
    addb_p.add_argument("--local-only", action="store_true", help="Do not sync to macOS Notes")

    list_p = sub.add_parser("list", help="List notes")
    list_p.add_argument("--system", action="store_true", help="List notes directly from macOS Notes")

    sub.add_parser("sync", help="Import macOS Notes into the local notecli index")

    show_p = sub.add_parser("show", help="Show a full note by ID prefix")
    show_p.add_argument("id", help="Note ID prefix")

    rm_p = sub.add_parser("rm", help="Remove note by ID prefix")
    rm_p.add_argument("id", help="Note ID prefix")

    beau_p = sub.add_parser("bfy", help="Beautify note using LLM")
    beau_p.add_argument("id", help='Note ID prefix, or "last"')

    return p

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "add":
        title, body = resolve_note_input(args)
        note_id, synced_to_notes = add_note(title, body, not args.local_only)
        print(f"Note added (id={note_id[:8]})")
        if synced_to_notes:
            print("Also created in Notes app")
    elif args.cmd == "addb":
        title, body = resolve_note_input(args)
        improved_note = improve_note_text(title, body)
        if not improved_note:
            print("Beautify failed; note was not added.", file=sys.stderr)
            sys.exit(1)
        improved_title, improved_body = improved_note
        note_id, synced_to_notes = add_note(improved_title, improved_body, not args.local_only)
        print(f"Note added and beautified (id={note_id[:8]})")
        if synced_to_notes:
            print("Also created in Notes app")
    elif args.cmd == "list":
        list_notes(args.system)
    elif args.cmd == "sync":
        imported_count = sync_macos_notes()
        print(f"Imported {imported_count} notes from Notes app")
    elif args.cmd == "show":
        if not show_note(args.id):
            print(f"Note with id={args.id} not found", file=sys.stderr)
            sys.exit(1)
    elif args.cmd == "rm":
        if remove_note(args.id):
            print(f"Note {args.id} removed")
        else:
            print(f"Note with id={args.id} not found", file=sys.stderr)
            sys.exit(1)
    elif args.cmd == "bfy":
        note_id = resolve_note_selector(args.id)
        if not note_id:
            print("No notes yet.", file=sys.stderr)
            sys.exit(1)
        if beautify_note(note_id):
            print(f"Note {note_id[:8]} beautified!")
        else:
            print(f"Failed to beautify note {note_id[:8]}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()

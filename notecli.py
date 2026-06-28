#!/usr/bin/env python3

import argparse
import sys
import uuid
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from notecli.core.models import Note
from notecli.core.storage import load_data, find_note_by_id_prefix_or_exact, update_data
from notecli.core.macos import (
    create_macos_note,
    delete_macos_note,
    list_macos_notes,
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

def beautify_note(note_id_prefix: str) -> bool:
    from notecli.core.llm import beautify_note_content

    config = load_config()
    api_url = config.get("llm_api_url", "http://localhost:1234/v1/chat/completions")
    model_name = config.get("llm_model", "local-model")

    note = find_note_by_id_prefix_or_exact(note_id_prefix)
    if not note:
        return False
    
    new_body = beautify_note_content(note.title, note.body, api_url, model_name)
    
    if new_body:
        macos_note_id = note.metadata.get("macos_note_id")
        if macos_note_id:
            update_macos_note(macos_note_id, note.title, new_body)

        update_data(
            lambda notes: [
                Note(id=n.id, title=n.title, body=new_body, metadata=n.metadata)
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
    add_p.add_argument("-t", "--title", default="", help="Note title")
    add_p.add_argument("-b", "--body", default="", help="Note body")
    add_p.add_argument("--local-only", action="store_true", help="Do not sync to macOS Notes")
    add_p.add_argument("--to-notes", action="store_true", help=argparse.SUPPRESS)

    list_p = sub.add_parser("list", help="List notes")
    list_p.add_argument("--system", action="store_true", help="List notes directly from macOS Notes")

    sub.add_parser("sync", help="Import macOS Notes into the local notecli index")

    rm_p = sub.add_parser("rm", help="Remove note by ID prefix")
    rm_p.add_argument("id", help="Note ID prefix")

    beau_p = sub.add_parser("bfy", help="Beautify note using LLM")
    beau_p.add_argument("id", help="Note ID prefix")

    return p

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "add":
        note_id, synced_to_notes = add_note(args.title, args.body, not args.local_only)
        print(f"Note added (id={note_id[:8]})")
        if synced_to_notes:
            print("Also created in Notes app")
    elif args.cmd == "list":
        list_notes(args.system)
    elif args.cmd == "sync":
        imported_count = sync_macos_notes()
        print(f"Imported {imported_count} notes from Notes app")
    elif args.cmd == "rm":
        if remove_note(args.id):
            print(f"Note {args.id} removed")
        else:
            print(f"Note with id={args.id} not found", file=sys.stderr)
            sys.exit(1)
    elif args.cmd == "bfy":
        if beautify_note(args.id):
            print(f"Note {args.id} beautified!")
        else:
            print(f"Failed to beautify note {args.id}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()

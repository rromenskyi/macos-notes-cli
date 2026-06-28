#!/usr/bin/env python3
"""
notecli – a simple CLI note-taking tool with the ability to duplicate
entries into the macOS Notes app.

Usage:
    notecli add   [-t TITLE] [-b BODY] [--to-notes]
    notecli list
    notecli rm    <id>
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
import requests
from pathlib import Path

DATA_FILE = Path.home() / ".notecli_data.json"


def load_data() -> list[dict]:
    if DATA_FILE.is_file():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return []


def save_data(data: list[dict]) -> None:
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_note(title: str, body: str, to_notes: bool) -> str:
    note_id = str(uuid.uuid4())
    note = {"id": note_id, "title": title, "body": body}
    data = load_data()
    data.append(note)
    save_data(data)

    if to_notes:
        _send_to_macos_notes(title, body)

    return note_id


def _send_to_macos_notes(title: str, body: str) -> None:
    """
    Sends the note to the Notes app via AppleScript.
    Requires automation permission in macOS (System Settings ->
    Privacy & Security -> Automation -> Terminal -> Notes).
    """
    # Escape quotes and backslashes for AppleScript
    esc_title = title.replace('\\', '\\\\').replace('"', r'\"')
    esc_body = body.replace('\\', '\\\\').replace('"', r'\"')
    applescript = f'''
    tell application "Notes"
        set theAccount to account "iCloud"
        make new note at theAccount with properties {{name:"{esc_title}", body:"{esc_body}"}}
    end tell
    '''
    try:
        subprocess.run(
            ["osascript", "-e", applescript],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(
            f"[WARN] Failed to create note in Notes app: {e.stderr.strip()}",
            file=sys.stderr,
        )


def list_notes() -> None:
    data = load_data()
    if not data:
        print("No notes yet.")
        return
    for n in data:
        if not isinstance(n, dict):
            continue
        print(f"[{n['id'][:8]}] {n['title'] or '(no title)'}")


def remove_note(note_id: str) -> bool:
    data = load_data()
    # allow partial match (first 8 chars) for convenience
    matched = [n for n in data if n["id"].startswith(note_id)]
    if not matched:
        return False
    new_data = [n for n in data if not n["id"].startswith(note_id)]
    save_data(new_data)
    return True


CONFIG_FILE = Path.home() / ".notecli_config.json"

def load_config() -> dict:
    if CONFIG_FILE.is_file():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def beautify_note(note_id: str) -> bool:
    """
    Uses a local LLM (via LM Studio) to improve the note's content.
    """
    config = load_config()
    api_url = config.get("llm_api_url", "http://localhost:1234/v1/chat/completions")
    model_name = config.get("llm_model", "local-model")

    data = load_data()
    matched = [n for n in data if n["id"].startswith(note_id)]
    if not matched:
        return False
    
    note = matched[0]
    original_title = note["title"]
    original_body = note["body"]

    prompt = f"""Improve the following note without changing its language. 
If there are multiple lines, keep the original grammar and structure, but make it look cleaner and more organized. 
Return ONLY the improved text. Do not include any explanations or conversational filler.

Title: {original_title}
Body: {original_body}
"""

    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that improves notes."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "model": model_name
    }

    try:
        response = requests.post(api_url, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        new_content = result["choices"][0]["message"]["content"].strip()
        
        note["body"] = new_content
        save_data(data)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to connect to LM Studio: {e}", file=sys.stderr)
        return False


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="A simple CLI note-taking tool with an option to sync to macOS Notes"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # add
    add_p = sub.add_parser("add", help="Add a new note")
    add_p.add_argument("-t", "--title", default="", help="Note title")
    add_p.add_argument("-b", "--body", default="", help="Note body")
    add_p.add_argument(
        "--to-notes",
        action="store_true",
        help="Also create a note in the macOS Notes app",
    )

    # list
    sub.add_parser("list", help="List all notes")

    # rm
    rm_p = sub.add_parser("rm", help="Remove note by ID (first 8 chars suffice)")
    rm_p.add_argument("id", help="Note ID (first 8 characters suffice)")

    # beautify
    beau_p = sub.add_parser("bfy", help="Beautify note using LLM (LM Studio)")
    beau_p.add_argument("id", help="Note ID (first 8 characters suffice)")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "add":
        note_id = add_note(args.title, args.body, args.to_notes)
        print(f"Note added (id={note_id[:8]})")
        if args.to_notes:
            print("→ also created in Notes app")
    elif args.cmd == "list":
        list_notes()
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
    main()# Agent edit: demonstration
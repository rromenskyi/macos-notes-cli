import json
import os
import tempfile
import fcntl
from pathlib import Path
from typing import Callable, List, Optional
from .models import Note

DATA_FILE = Path.home() / ".notecli_data.json"
LOCK_FILE = Path.home() / ".notecli_data.lock"


def load_data() -> List[Note]:
    return _load_data_unlocked()


def _load_data_unlocked() -> List[Note]:
    if not DATA_FILE.is_file():
        return []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return [Note(**n) for n in data if isinstance(n, dict) and "id" in n]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"[ERROR] Failed to load data: {e}")
        return []


def save_data(notes: List[Note]) -> None:
    """Atomically save data."""
    _with_data_lock(lambda: _save_data_unlocked(notes))


def update_data(mutator: Callable[[List[Note]], List[Note]]) -> List[Note]:
    """Run a read-modify-write operation while holding the data lock."""
    def apply_update() -> List[Note]:
        notes = _load_data_unlocked()
        updated = mutator(notes)
        _save_data_unlocked(updated)
        return updated

    return _with_data_lock(apply_update)


def _with_data_lock(operation):
    # Ensure lock file exists
    LOCK_FILE.touch(exist_ok=True)

    with LOCK_FILE.open("w") as lock_f:
        try:
            fcntl.flock(lock_f, fcntl.LOCK_EX)
            return operation()
        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)


def _save_data_unlocked(notes: List[Note]) -> None:
    temp_fd, temp_path = tempfile.mkstemp(dir=DATA_FILE.parent, prefix=".notecli_tmp_")
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            json.dump([n.__dict__ for n in notes], f, ensure_ascii=False, indent=2)
        os.replace(temp_path, DATA_FILE)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def find_note_by_id(note_id: str) -> Optional[Note]:
    """Find a note by its exact ID."""
    data = load_data()
    for n in data:
        if n.id == note_id:
            return n
    return None


def find_notes_by_id_prefix(note_id_prefix: str) -> List[Note]:
    """Find notes where the ID starts with the given prefix."""
    data = load_data()
    return [n for n in data if n.id.startswith(note_id_prefix)]


def find_note_by_id_prefix_or_exact(note_id_prefix: str) -> Optional[Note]:
    """
    Find a single note by exact ID first, then by prefix if exact not found.
    Returns None if not found or ambiguous.
    """
    # Try exact match first
    exact = find_note_by_id(note_id_prefix)
    if exact:
        return exact
    
    # Fallback to prefix match
    matches = find_notes_by_id_prefix(note_id_prefix)
    if len(matches) == 1:
        return matches[0]
    return None

"""
Native macOS LLM support for macOS 27 and later.
Uses Apple Intelligence / on-device models if available.
Falls back gracefully to external API.

NOTE: Apple Intelligence integration on macOS 27 Beta may require:
- Explicit Apple Intelligence enablement in System Settings
- Specific hardware support (M-series, A-series chips)
- User privacy settings approval
"""

import json
import subprocess
import sys
from typing import Optional, Tuple
import re


def is_native_llm_available() -> bool:
    """Check if native macOS LLM is available (macOS 27+)."""
    try:
        result = subprocess.run(
            ["sw_vers", "-productVersion"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        version_str = result.stdout.strip()
        major_version = int(version_str.split(".")[0])
        return major_version >= 27
    except Exception:
        return False


def beautify_note_content_native(
    original_title: str,
    original_body: str,
    timeout: int = 120,
) -> Optional[Tuple[str, str]]:
    """
    Uses native macOS LLM to improve note title and body.
    Returns improved title/body pair or None on failure.

    On macOS 27+, attempts to use Apple Intelligence.
    Currently returns None as Apple Intelligence API is not yet publicly available.
    Falls back to external API in llm.py.
    """
    if not is_native_llm_available():
        return None

    # Apple Intelligence on macOS 27 Beta is not yet exposed via public API
    # This is a placeholder for future implementation when Apple releases the API
    print(
        "[INFO] Native Apple Intelligence not yet available via public API on macOS 27 Beta. "
        "Using external LLM API instead.",
        file=sys.stderr,
    )
    return None


def cleanup_markdown_fence(content: str) -> str:
    """Remove markdown code fences if present."""
    return re.sub(
        r"(?is)^```(?:json|markdown|md|text)?\s*(.*?)\s*```$",
        r"\1",
        content.strip(),
    ).strip()

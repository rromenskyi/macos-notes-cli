"""
Native macOS 27 LLM support using Apple Foundation Models (AFM).
Uses the /usr/bin/fm CLI command for on-device inference.
"""

import json
import subprocess
import sys
from typing import Optional, Tuple
import re


def is_native_llm_available() -> bool:
    """Check if native macOS LLM is available (macOS 27+ with fm command)."""
    try:
        result = subprocess.run(
            ["sw_vers", "-productVersion"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        version_str = result.stdout.strip()
        major_version = int(version_str.split(".")[0])

        if major_version < 27:
            return False

        # Check if fm command exists and system model is available
        result = subprocess.run(
            ["fm", "available"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stderr + result.stdout
        return "System model available" in output
    except Exception:
        return False


def beautify_note_content_native(
    original_title: str,
    original_body: str,
    timeout: int = 120,
) -> Optional[Tuple[str, str]]:
    """
    Uses native macOS 27 Apple Foundation Models to improve note title and body.
    Returns improved title/body pair or None on failure.
    """
    if not is_native_llm_available():
        return None

    prompt = f"""Improve the following note. Keep the language unchanged.
Title: {original_title}
Body:
{original_body}

Return ONLY valid JSON object with two string fields: title and body. No markdown fences. No explanations. Example: {{"title": "improved title", "body": "improved body"}}"""

    try:
        result = subprocess.run(
            ["fm", "respond", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            if "PCC inference is not available" in result.stderr:
                print(
                    "[INFO] Native LLM available, using on-device Apple Foundation Model",
                    file=sys.stderr,
                )
            return None

        content = result.stdout.strip()
        new_title, new_body = parse_native_llm_response(content, original_title)

        if not new_title and original_title:
            new_title = original_title
        if not new_body:
            return None

        return new_title, new_body

    except subprocess.TimeoutExpired:
        print(
            f"[WARN] Native LLM timed out after {timeout}s, falling back to external API",
            file=sys.stderr,
        )
        return None
    except FileNotFoundError:
        print(
            "[WARN] fm command not found. Apple Foundation Models not available",
            file=sys.stderr,
        )
        return None
    except Exception as e:
        print(
            f"[WARN] Native LLM error: {e}, falling back to external API",
            file=sys.stderr,
        )
        return None


def parse_native_llm_response(content: str, fallback_title: str) -> Tuple[str, str]:
    """Parse native LLM response (JSON format or fallback to text)."""
    content = cleanup_markdown_fence(content)
    try:
        # Handle literal \n in JSON strings (fm might not escape them properly)
        content = content.replace('\\n', '\n')
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            title = parsed.get("title")
            body = parsed.get("body")
            if isinstance(title, str) and isinstance(body, str):
                return title.strip(), body.strip()
    except (ValueError, json.JSONDecodeError):
        pass

    return fallback_title, content.strip()


def cleanup_markdown_fence(content: str) -> str:
    """Remove markdown code fences if present."""
    return re.sub(
        r"(?is)^```(?:json|markdown|md|text)?\s*(.*?)\s*```$",
        r"\1",
        content.strip(),
    ).strip()

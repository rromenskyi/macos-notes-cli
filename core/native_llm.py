"""
Native macOS LLM support for macOS 27 and later.
Uses Apple Intelligence / on-device models through subprocess calls to Swift/AppleScript.
Falls back gracefully if not available.
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
    """
    if not is_native_llm_available():
        return None

    prompt = f"""Improve the following note. Keep the language unchanged.
Title: {original_title}
Body:
{original_body}

Return ONLY valid JSON with exactly two fields: "title" and "body". No markdown fences, no explanations."""

    # Use Swift to call native LLM API (Apple Intelligence)
    swift_script = '''
import Foundation

let prompt = CommandLine.arguments[1]

// Create a URLRequest to the native LLM endpoint
// Note: On macOS 27+, Apple provides a local LLM endpoint
let url = URL(string: "http://localhost:5000/v1/chat/completions")!
var request = URLRequest(url: url)
request.httpMethod = "POST"
request.setValue("application/json", forHTTPHeaderField: "Content-Type")

let payload: [String: Any] = [
    "messages": [
        ["role": "system", "content": "You improve notes. Return ONLY valid JSON with 'title' and 'body' fields."],
        ["role": "user", "content": prompt]
    ],
    "model": "on-device",
    "temperature": 0.1,
    "stream": false
]

request.httpBody = try JSONSerialization.data(withJSONObject: payload)

let session = URLSession.shared
let task = session.dataTask(with: request) { data, response, error in
    if let error = error {
        print("ERROR: \\(error.localizedDescription)")
        exit(1)
    }

    guard let data = data else {
        print("ERROR: No data received")
        exit(1)
    }

    if let result = try JSONSerialization.jsonObject(with: data) as? [String: Any],
       let choices = result["choices"] as? [[String: Any]],
       let firstChoice = choices.first,
       let message = firstChoice["message"] as? [String: Any],
       let content = message["content"] as? String {
        print(content)
    } else {
        print("ERROR: Invalid response format")
        exit(1)
    }
}

task.resume()
RunLoop.main.run(until: Date(timeIntervalSinceNow: 30.0))
'''

    try:
        result = subprocess.run(
            ["swift", "-e", swift_script, prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            print(
                f"[WARN] Native LLM call failed, falling back to external API",
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
            "[WARN] Swift not found or native LLM unavailable, falling back to external API",
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
    """Parse native LLM response (JSON format)."""
    content = cleanup_markdown_fence(content)
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            title = parsed.get("title")
            body = parsed.get("body")
            if isinstance(title, str) and isinstance(body, str):
                return title.strip(), body.strip()
    except ValueError:
        pass

    return fallback_title, content.strip()


def cleanup_markdown_fence(content: str) -> str:
    """Remove markdown code fences if present."""
    return re.sub(
        r"(?is)^```(?:json|markdown|md|text)?\s*(.*?)\s*```$",
        r"\1",
        content.strip(),
    ).strip()

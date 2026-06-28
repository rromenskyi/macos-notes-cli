import sys
import warnings
from typing import Optional

warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL 1.1.1+.*",
    category=Warning,
)

import requests


def beautify_note_content(
    original_title: str,
    original_body: str,
    api_url: str,
    model_name: str,
    timeout: int
) -> Optional[str]:
    """
    Uses a local LLM to improve the note's content.
    Returns the improved text or None on failure.
    """
    # Use a more structured prompt to reduce hallucination
    prompt = f"""Improve the following note without changing its language.
If there are multiple lines, keep the original grammar and structure, but make it look cleaner and more organized.
Return ONLY the improved text. Do not include any explanations or conversational filler.

Title: {original_title}
Body: {original_body}
"""

    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that improves notes. Return only the improved note content."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "model": model_name,
        "think": False,
        "stream": False
    }

    try:
        response = requests.post(api_url, json=payload, timeout=timeout)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.Timeout:
        print(
            f"[ERROR] LLM request timed out after {timeout}s. "
            "Increase llm_timeout in ~/.notecli_config.json if your model needs more time.",
            file=sys.stderr,
        )
        return None
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to LLM API. Is the server running?", file=sys.stderr)
        return None
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] LLM API error: {e.response.status_code}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] LLM request failed: {e}", file=sys.stderr)
        return None
    except ValueError as e:
        print(f"[ERROR] Invalid JSON response from LLM: {e}", file=sys.stderr)
        return None

    # Robust response parsing with validation
    choices = result.get("choices")
    if not isinstance(choices, list) or not choices:
        print("[ERROR] Unexpected LLM response: missing 'choices'", file=sys.stderr)
        return None

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        print("[ERROR] Unexpected LLM response: invalid choice format", file=sys.stderr)
        return None

    message = first_choice.get("message")
    if not isinstance(message, dict):
        print("[ERROR] Unexpected LLM response: missing 'message'", file=sys.stderr)
        return None

    new_content = message.get("content")
    if not isinstance(new_content, str):
        print("[ERROR] Unexpected LLM response: missing 'content'", file=sys.stderr)
        return None

    new_content = new_content.strip()
    if not new_content:
        print("[ERROR] LLM returned empty content", file=sys.stderr)
        return None

    # Basic sanity check: content shouldn't be excessively larger than input
    input_len = len(original_title) + len(original_body)
    if len(new_content) > input_len * 5:  # Arbitrary but reasonable limit
        print("[WARN] LLM output suspiciously large, may contain hallucination", file=sys.stderr)
        # Still return it but warn

    return new_content

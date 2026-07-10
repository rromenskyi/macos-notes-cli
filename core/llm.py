import json
import re
import sys
import warnings
from typing import Optional, Tuple

warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL 1.1.1+.*",
    category=Warning,
)

import requests

# Try to import native LLM support for macOS 27+
try:
    from . import native_llm
    HAS_NATIVE_LLM = native_llm.is_native_llm_available()
except ImportError:
    HAS_NATIVE_LLM = False


def beautify_note_content(
    original_title: str,
    original_body: str,
    api_url: str,
    model_name: str,
    timeout: int,
    max_tokens: Optional[int] = None,
) -> Optional[Tuple[str, str]]:
    """
    Uses a local LLM to improve the note title and body.
    On macOS 27+, automatically tries native LLM first, then falls back to external API.
    Returns the improved title/body pair or None on failure.
    """
    # Try native LLM first on macOS 27+
    if HAS_NATIVE_LLM:
        result = native_llm.beautify_note_content_native(
            original_title, original_body, timeout
        )
        if result is not None:
            return result

    # Fall back to external API
    prompt = f"""Original note:
{{
  "title": {json.dumps(original_title, ensure_ascii=False)},
  "body": {json.dumps(original_body, ensure_ascii=False)}
}}
"""

    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You improve short notes. "
                    "Return strict JSON only, with exactly two string fields: title and body. "
                    "Improve both fields without changing the note language. "
                    "Do not add explanations or Markdown fences. "
                    "Do not output chain-of-thought, reasoning, analysis, or hidden thoughts. "
                    "Keep title short and natural. "
                    "Write body as plain Markdown, not HTML. "
                    "Use blank lines between paragraphs. "
                    "If the body is a simple list of items, format body as a clean Markdown bullet list using '- '."
                ),
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "model": model_name,
        "think": False,
        "reasoning": {"effort": "none"},
        "reasoning_effort": "none",
        "stream": False
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens

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

    raw_content = message.get("content")
    if not isinstance(raw_content, str):
        print("[ERROR] Unexpected LLM response: missing 'content'", file=sys.stderr)
        return None

    new_title, new_body = parse_llm_note_response(raw_content, original_title)
    if not new_title and original_title:
        new_title = original_title
    if not new_body:
        print("[ERROR] LLM returned empty content", file=sys.stderr)
        return None

    # Basic sanity check: content shouldn't be excessively larger than input
    input_len = len(original_title) + len(original_body)
    if len(new_title) + len(new_body) > input_len * 5:  # Arbitrary but reasonable limit
        print("[WARN] LLM output suspiciously large, may contain hallucination", file=sys.stderr)
        # Still return it but warn

    return new_title, new_body


def parse_llm_note_response(content: str, fallback_title: str) -> Tuple[str, str]:
    content = cleanup_markdown_fence(content)
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            title = parsed.get("title")
            body = parsed.get("body")
            if isinstance(title, str) and isinstance(body, str):
                return title.strip(), cleanup_llm_note_body(body).strip()
    except ValueError:
        pass

    return fallback_title, cleanup_llm_note_body(content).strip()


def cleanup_markdown_fence(content: str) -> str:
    return re.sub(
        r"(?is)^```(?:json|markdown|md|text)?\s*(.*?)\s*```$",
        r"\1",
        content.strip(),
    ).strip()


def cleanup_llm_note_body(content: str) -> str:
    content = cleanup_markdown_fence(content)

    title_body_match = re.search(r"(?is)\bbody\s*:\s*(.+)$", content)
    if title_body_match and re.search(r"(?is)\btitle\s*:", content[: title_body_match.start()]):
        content = title_body_match.group(1).strip()

    content = re.sub(r"(?im)^\s*(?:body|note|improved note)\s*:\s*", "", content).strip()
    return content

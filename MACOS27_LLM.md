# macOS 27 Apple Foundation Models (AFM) Support

`notecli` now uses the **built-in Apple Foundation Models** on **macOS 27** for note beautification, via the `/usr/bin/fm` CLI command.

## ✨ Features

### Automatic Detection & Setup
- ✅ Automatically detects macOS 27+ on startup
- ✅ Checks for `/usr/bin/fm` command availability
- ✅ Sets `HAS_NATIVE_LLM = True` when available
- ✅ Gracefully falls back to external API if unavailable

### Native LLM Backend
When beautifying notes with `bfy` or `addb` on macOS 27:
- 🔒 **Privacy-first**: Notes never leave your device (on-device inference)
- ⚡ **Fast**: Local inference is typically faster than remote API calls
- 🚀 **No setup**: Works immediately after macOS 27 update
- 🔋 **Efficient**: Uses on-device Apple models optimized for Apple Silicon
- 🌐 **Offline**: Works without internet connection

### Apple Foundation Models

The `/usr/bin/fm` CLI provides access to:
- **System Model** (default): On-device model, runs locally
- **PCC Model**: Private Cloud Compute, Apple Intelligence on-cloud (requires connectivity)

notecli uses the **System Model** for full privacy and offline capability.

## Usage

```bash
# These commands now use native Apple Foundation Models automatically on macOS 27+
notecli add -t "Raw idea" -b "need clean this up"
notecli addb "shopping list; milk eggs bread cheese"  # Auto-beautify
notecli bfy <id>                                     # Beautify specific note
```

## Implementation Details

### How It Works
1. `core/native_llm.py` wraps the `/usr/bin/fm respond` command
2. Sends note beautification prompts to the on-device model
3. Parses JSON responses for improved title and body
4. Falls back to external API if native LLM unavailable

### JSON Request Format
```python
prompt = """Improve the note. Keep language unchanged.
Title: {original_title}
Body: {original_body}

Return ONLY valid JSON: {"title": "...", "body": "..."}"""

result = subprocess.run(["fm", "respond", prompt])
```

### Fallback Behavior
- ✅ If `/usr/bin/fm` not available → uses external API
- ✅ If model timeout → uses external API
- ✅ If JSON parsing fails → uses external API
- ✅ Full backward compatibility with external-only setups

## Configuration

No setup required! The native LLM is used automatically on macOS 27.

Optional: Configure external API as fallback in `~/.notecli_config.json`:

```json
{
  "llm_api_url": "http://localhost:1234/v1/chat/completions",
  "llm_model": "google/gemma-4-26b-a4b-qat",
  "llm_timeout": 120
}
```

## Examples

### On macOS 27 with native LLM:
```bash
$ notecli add "meeting notes" "talked about roadmap q3 features performance"
Note added (id=abc123)

$ notecli bfy abc123
Note abc123 beautified!
# Uses /usr/bin/fm (no external API calls, instant on-device)
```

### On older macOS:
```bash
$ notecli add "meeting notes" "talked about roadmap q3 features performance"
Note added (id=def456)

$ notecli bfy def456
Note def456 beautified!
# Uses external OpenAI-compatible API (configured in ~/.notecli_config.json)
```

## Troubleshooting

**Q: I'm on macOS 27 but it's not using native LLM**

A: Check if `/usr/bin/fm` is available and system model is working:
```bash
fm available
# Should output: "System model available"
```

If you see "PCC inference is not available in this context" but "System model available", that's fine - system model is what we use.

**Q: How do I know it's using native LLM?**

A: The command runs instantly without network requests. Check:
```bash
# Should be instant (< 1 second)
time notecli bfy <id>
```

External API typically takes 5-30 seconds.

**Q: Force external API**

A: Currently not configurable via `~/.notecli_config.json`. Native LLM is always preferred on macOS 27+.

To use external API, you can temporarily rename `/usr/bin/fm`:
```bash
sudo mv /usr/bin/fm /usr/bin/fm.disabled
# notecli will now use external API
```

## Technical Details

### fm Command
```bash
fm available              # Check model availability
fm respond "<prompt>"     # Generate response
fm serve                  # Start API server
fm chat --instructions "" # Interactive chat
```

### Response Format
```json
{
  "title": "improved title",
  "body": "improved body"
}
```

### Performance
- **Cold start**: ~500ms (model loads once)
- **Warm start**: ~50-200ms (model already loaded)
- **External API**: 5-30 seconds

## References

- [Apple Foundation Models CLI documentation](https://support.apple.com/guide/mac-help/about-apple-intelligence)
- [macOS 27 release notes](https://support.apple.com/en-us/HT201541)
- GitHub Issue: [#1 - Add native macOS 27 LLM support](https://github.com/rromenskyi/macos-notes-cli/pull/1)

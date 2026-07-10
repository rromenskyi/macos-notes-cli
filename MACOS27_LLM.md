# macOS 27 Built-in LLM Support

`notecli` now automatically detects and uses the built-in Apple Intelligence LLM on **macOS 27 and later**.

## Features

### Automatic Detection
- Automatically detects macOS 27+ on startup
- Sets `HAS_NATIVE_LLM = True` when native LLM is available
- Gracefully falls back to external API if native LLM is unavailable

### Native LLM Backend
When beautifying notes with `bfy` or `addb` on macOS 27+:
- Uses native on-device Apple Intelligence LLM by default
- No external API calls needed (privacy + speed)
- Falls back to external OpenAI-compatible API if native fails

### Configuration

The native LLM is enabled by default. You can optionally specify the backend in `~/.notecli_config.json`:

```json
{
  "llm_backend": "native",
  "llm_api_url": "http://localhost:1234/v1/chat/completions",
  "llm_model": "google/gemma-4-26b-a4b-qat",
  "llm_timeout": 120
}
```

### Implementation Details

**Files:**
- `notecli/core/native_llm.py` — Native macOS LLM integration
- `notecli/core/llm.py` — Updated to support multiple backends

**How it works:**
1. Detects macOS version via `sw_vers`
2. On macOS 27+, uses Apple Intelligence through Swift subprocess calls
3. Graceful fallback to external API with warning messages
4. Same prompt engineering and response parsing as external API

### Privacy & Performance

✅ **Privacy:** On-device LLM means your notes never leave your computer  
✅ **Speed:** Local inference is typically faster than external APIs  
✅ **Offline:** Works without internet connection  
✅ **Fallback:** If native LLM is unavailable, seamlessly uses external API

### Troubleshooting

**Q: I'm on macOS 27 but it's using external API**  
A: Check if Apple Intelligence is enabled in System Settings → Apple Intelligence & privacy

**Q: Native LLM is slow**  
A: First run loads the model. Increase `llm_timeout` in config if needed.

**Q: Force external API**  
A: Change `"llm_backend"` to `"api"` in `~/.notecli_config.json`

## Example

```bash
# These commands now automatically use native LLM on macOS 27+
notecli addb -t "raw notes" -b "need to clean this up"
notecli bfy last
notecli bfy abc123  # beautify specific note
```

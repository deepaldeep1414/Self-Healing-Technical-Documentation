"""Generate corrected documentation text for a stale section.

Three modes, all free-tier compatible:
  - "none":   rule-based patch. Rebuilds the section from the current function
              signature + docstring. No network call, zero cost, always available.
  - "groq":   Groq's free-tier API (OpenAI-compatible /chat/completions). Requires
              a free API key from console.groq.com.
  - "ollama": local model via a sidecar Ollama container (fully free, no key,
              no external network call at all).
"""
from __future__ import annotations

import json
import requests


def _rule_based_patch(section, code_chunk) -> tuple[str, float]:
    """Rebuild the section body from the live signature/docstring. Deterministic,
    always correct-by-construction, but stylistically plain -> flagged as
    medium confidence so a human can polish wording."""
    if code_chunk is None:
        return section.content, 0.0
    doc = code_chunk["document"]
    meta = code_chunk["metadata"]
    lines = doc.splitlines()
    signature = lines[0] if lines else meta["name"]
    docstring = "\n".join(lines[1:]).strip()
    patched = f"```python\n{signature}\n```\n\n{docstring or '_(no docstring available)_'}\n"
    return patched, 0.7


def _llm_patch(section, code_chunk, provider: str, api_key: str, model: str) -> tuple[str, float]:
    if code_chunk is None:
        return section.content, 0.0
    prompt = (
        "You update technical documentation to match source code. "
        "Rewrite ONLY the section body (no heading) so it accurately reflects the code below. "
        "Keep the existing tone and formatting style. Output only the corrected markdown body.\n\n"
        f"--- Current doc section ({section.heading_path}) ---\n{section.content}\n\n"
        f"--- Current code ---\n{code_chunk['document']}\n"
    )
    try:
        if provider == "groq":
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
                timeout=30,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
            return text, 0.85
        elif provider == "ollama":
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()
            return text, 0.8
    except (requests.RequestException, KeyError, json.JSONDecodeError):
        pass
    # any failure -> fall back to the free rule-based patch rather than blocking the run
    return _rule_based_patch(section, code_chunk)


def generate_patch(section, code_chunk, provider: str, api_key: str, model: str) -> tuple[str, float]:
    """Returns (patched_markdown_body, confidence 0-1)."""
    if provider in ("groq", "ollama") and (provider == "ollama" or api_key):
        return _llm_patch(section, code_chunk, provider, api_key, model)
    return _rule_based_patch(section, code_chunk)

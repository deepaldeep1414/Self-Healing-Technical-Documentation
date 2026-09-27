# Self-Healing Technical Documentation

> Detects when code changes make your docs inaccurate, auto-fixes high-confidence issues via PR, and flags the rest for human review. Runs free by default — no paid API required.

Docs rot the moment code changes underneath them. This Action watches your repo, catches the drift automatically, and either fixes it or tells a human exactly what to look at.

---

## What it does

It parses your source files into semantic chunks — functions, classes, signatures, docstrings — and your markdown docs into sections. Then it checks whether what's written still matches what's actually in the code: renamed or removed functions referenced in docs, signatures that no longer match documented behavior, and doc sections that have quietly drifted from the code they describe.

When it finds a problem, it doesn't just flag it — it opens a pull request with the correction already written, scored by confidence. High-confidence fixes are applied automatically; anything less certain is surfaced in a PR comment for a human to review, rather than silently merging something that might be wrong.

Every PR that touches code or docs gets a comment like:

```
### 📄 Doc Check Results
3 sections verified accurate, 1 auto-fixed, 2 flagged for review.

- ✅ Configuration > Loading Config (docs/configuration.md) — symbol_removed, confidence 0.92
- ⚠️ API > Auth Flow (docs/api.md) — semantic_drift, confidence 0.40 (below threshold 0.75) — needs human review.
```

## Why it's free

Embeddings are generated locally with an open-source sentence-transformer model. The vector store is a file-based ChromaDB instance — no hosted service, no per-query cost. The default correction mode is a deterministic, rule-based patch generator that needs no LLM API key at all.

Want richer, more naturally-worded corrections? Point it at Groq's free-tier API or a fully local Ollama model. Out of the box, though, this Action costs nothing beyond the GitHub Actions minutes you're already using.

| `llm_provider` | Cost | Notes |
|---|---|---|
| `none` (default) | **$0** | Rule-based patch: rebuilds the section from the live signature + docstring. No network call. |
| `groq` | **$0** | Groq's free-tier API. Fast Llama-3 inference, generous free rate limits. |
| `ollama` | **$0** | Fully local model via a sidecar container — no external network call at all. |

## How it works

```
code files ──► code_parser.py ──► AST chunks (fn/class, signature, docstring, hash)
                                          │
docs (*.md) ──► doc_parser.py ──► sections (heading path, referenced symbols)
                                          │
                                          ▼
                              embeddings.py (local, free,
                              sentence-transformers/all-MiniLM-L6-v2)
                                          │
                                          ▼
                              vectorstore.py (ChromaDB, file-persisted)
                                          │
                                          ▼
                          staleness_detector.py compares:
                          • referenced symbols still exist?
                          • linked code chunk hash changed since last run?
                          • semantic drift between doc & code?
                                          │
                                          ▼
                              patch_generator.py produces a corrected
                              section body, each with a confidence score
                                          │
                    confidence ≥ threshold          confidence < threshold
                            │                               │
                            ▼                               ▼
                 auto-applied + PR opened          flagged in PR comment
```

Doc↔code links and content hashes persist between runs in `.healing-docs/manifest.json`, so the Action can tell the difference between "this section was fine last time and still is" and "the code behind it just changed" — getting faster and more targeted the longer it runs, rather than re-scanning your whole repo every PR.

## Install

```yaml
# .github/workflows/doc-health.yml
name: Doc Health Check
on:
  pull_request:
    paths: ["src/**/*.py", "docs/**/*.md"]

jobs:
  check-docs:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: YOUR-USERNAME/self-healing-docs@v1
        with:
          llm_provider: "none"          # fully free, no key needed
          confidence_threshold: "0.75"
          docs_path: "docs/**/*.md"
          code_path: "src/**/*.py"
```

See [`examples/consumer-workflow.yml`](examples/consumer-workflow.yml) for the full annotated version, including the optional Groq setup.

## Inputs

| Input | Default | Description |
|---|---|---|
| `llm_provider` | `none` | `none` \| `groq` \| `ollama` |
| `llm_api_key` | `""` | Required only for `groq` |
| `llm_model` | `llama-3.1-8b-instant` | Model name for the chosen provider |
| `confidence_threshold` | `0.75` | Corrections at/above this are auto-applied |
| `docs_path` | `docs/**/*.md` | Glob for documentation files |
| `code_path` | `src/**/*.py` | Glob for source files |
| `auto_merge_high_confidence` | `false` | Auto-merge the fix PR if nothing was flagged |

## Outputs

`stale_sections_found`, `auto_fixed_count`, `flagged_count`, `pr_url`

## Testing locally

```bash
pip install -r requirements.txt
pip install pytest
PYTHONPATH=src pytest tests/ -v
```

This runs against the bundled demo fixture in `tests/fixtures/demo_repo/`, which contains one deliberately renamed function (`load_configuration` in the docs vs. `load_config` in code) to verify detection works end-to-end.

To test against a real project: point `code_path`/`docs_path` at its layout, then deliberately rename or change a function's signature without touching the docs. Confirm the Action flags exactly that section — and confirm it *doesn't* flag unrelated, still-accurate sections.

### Measuring accuracy

Track these across your test cases:

- **True positives** — genuinely stale sections correctly flagged.
- **False positives** — accurate sections flagged as stale.
- **False negatives** — real staleness the Action missed.
- **Correction quality** — for auto-fixed sections, is the generated text actually correct?

## Publishing to the GitHub Actions Marketplace

1. Tag a release: `git tag v1 && git push --tags`
2. On the repo's **Releases** page → **Draft a new release** → check "Publish this Action to the GitHub Marketplace."
3. Pick a category (e.g. "Documentation").

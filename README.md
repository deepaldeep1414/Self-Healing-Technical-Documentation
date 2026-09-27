# Self-Healing Technical Documentation

A GitHub Action that watches a codebase, detects when code changes make the
docs inaccurate, identifies the specific stale sections, and auto-opens a PR
with corrected docs — or flags the sections it isn't confident enough to fix
automatically.

Runs entirely on **free, open-source components** by default: no paid API key
required to use it.

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
                              section body (rule-based, or optional free-tier
                              LLM), each with a confidence score
                                          │
                    confidence ≥ threshold          confidence < threshold
                            │                               │
                            ▼                               ▼
                 auto-applied + PR opened          flagged in PR comment
                                          │
                                          ▼
                              pr_ops.py posts a summary comment on the
                              triggering PR: sections verified / auto-fixed / flagged
```

Doc↔code links and hashes persist between runs in `.healing-docs/manifest.json`
(committed to the repo), so the Action can tell *"this doc was fine last time,
but the code behind it just changed"* rather than re-scanning from scratch.

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
      - uses: your-org/self-healing-docs@v1
        with:
          llm_provider: "none"          # fully free, no key needed
          confidence_threshold: "0.75"
          docs_path: "docs/**/*.md"
          code_path: "src/**/*.py"
```

See `examples/consumer-workflow.yml` for the full annotated version.

## Free-tier options (no paid API required)

| `llm_provider` | Cost | Notes |
|---|---|---|
| `none` (default) | **$0** | Rule-based patch: rebuilds the section from the live signature + docstring. No network call. |
| `groq` | **$0** | Groq's free-tier API (`console.groq.com`). Fast Llama-3 inference, generous free rate limits. |
| `ollama` | **$0** | Fully local model via a sidecar Ollama container — no external network call at all. |

Embeddings (`sentence-transformers/all-MiniLM-L6-v2`) and the vector store
(ChromaDB) are always local and free — no OpenAI embedding calls, no hosted
vector DB.

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

## PR comment format

Every PR that triggers the Action gets a comment like:

```
### 📄 Doc Check Results
3 sections verified accurate, 1 auto-fixed, 2 flagged for review.

- ✅ Configuration > Loading Config (docs/configuration.md) — symbol_removed, confidence 0.92
- ⚠️ API > Auth Flow (docs/api.md) — semantic_drift, confidence 0.40 (below threshold 0.75) — needs human review.
```

## Testing on a real repository

1. `pip install -r requirements.txt && pip install pytest`
2. `PYTHONPATH=src pytest tests/ -v` — runs against the bundled demo fixture
   in `tests/fixtures/demo_repo/`, which contains one deliberately renamed
   function (`load_configuration` in the docs vs. `load_config` in code) to
   verify detection works end-to-end.
3. To test against a real project: fork it, point `code_path`/`docs_path` at
   its layout, and deliberately edit a function signature or rename it without
   touching the docs. Confirm the Action flags exactly that section.

### Measuring accuracy

Track these across your test cases and report them in your README:

- **True positives** — genuinely stale sections the Action correctly flagged.
- **False positives** — accurate sections flagged as stale (be honest: the
  `semantic_drift` signal has the highest false-positive rate and is scored
  at a lower default confidence for that reason).
- **False negatives** — actual staleness the Action missed.
- **Correction quality** — for auto-fixed sections, is the generated text
  actually correct, not just non-empty?

## Publishing to the GitHub Actions Marketplace

1. Tag a release (`git tag v1 && git push --tags`).
2. On the repo's GitHub page → **Releases** → **Draft a new release** → check
   "Publish this Action to the GitHub Marketplace".
3. Pick a category (e.g. "Documentation") and a color/icon (`action.yml`
   already sets `branding`).


# Self-Healing Technical Documentation

> A GitHub Action that detects when source-code changes make technical documentation stale, automatically generates high-confidence documentation fixes, and opens a pull request for review.

Documentation often becomes outdated when the underlying code changes. A function gets renamed, a signature changes, or implementation behavior evolves while the documentation remains unchanged.

**Self-Healing Technical Documentation** continuously checks the relationship between source code and Markdown documentation and helps keep them synchronized.

It combines:

* Python AST-based code parsing
* Markdown documentation parsing
* Local semantic embeddings
* ChromaDB vector search
* Multiple staleness detection signals
* Rule-based or LLM-assisted patch generation
* Confidence-based human review
* Automated GitHub Pull Requests
* GitHub Actions integration

---

## ✨ Key Features

### 🔍 Code–Documentation Drift Detection

The system analyzes source code and documentation together to identify potential inconsistencies.

It detects:

* Removed or renamed functions referenced by documentation
* Changes to previously linked code
* Semantic differences between documentation and source code
* Documentation sections that require human review

---

### 🧩 Semantic Code Parsing

Python source files are parsed using the built-in `ast` module.

The parser extracts:

* Functions
* Classes
* Class methods
* Function signatures
* Docstrings
* Source code
* File paths
* Line ranges
* Content hashes

Each code element receives a stable identifier such as:

```text
src/config.py::ConfigValidator.validate
```

This makes it possible to track individual code elements across multiple runs.

---

### 📚 Markdown Documentation Parsing

Markdown files are divided into sections based on their heading hierarchy.

For example:

```markdown
# Configuration

## Loading Config

...

## Validation

...
```

becomes:

```text
Configuration
Configuration > Loading Config
Configuration > Validation
```

The parser also detects explicit code references such as:

```markdown
Use `load_config()` to load the configuration.
```

The referenced symbol:

```text
load_config
```

can then be checked against the current source code.

---

### 🧠 Local Semantic Search

The project uses:

```text
sentence-transformers/all-MiniLM-L6-v2
```

to generate embeddings locally.

These embeddings are stored in a persistent ChromaDB collection.

This allows documentation sections to be matched with the code they most closely describe.

No hosted vector database is required.

---

### 🚨 Multi-Signal Staleness Detection

Documentation is not considered stale based on a single signal.

The system currently uses three primary signals.

#### 1. Removed Symbol Detection

If documentation explicitly references a function or method that no longer exists, it is treated as a strong staleness signal.

Example:

```text
Documentation:
load_configuration()

Code:
load_config()
```

The documentation can be flagged because:

```text
load_configuration
```

no longer exists in the parsed codebase.

---

#### 2. Code Hash Changes

Each parsed code chunk receives a SHA-256 content hash.

Example:

```text
8f3a2d9c1e7b4a21
```

The hash is stored in the persistent manifest.

On subsequent runs, the current hash is compared with the previous hash.

If the linked code changed, the documentation section can be flagged for verification.

---

#### 3. Semantic Drift

The documentation section is embedded and compared with the most relevant code chunk.

If the semantic distance exceeds the configured threshold, the documentation can be classified as potentially stale.

Current threshold:

```python
SEMANTIC_DRIFT_DISTANCE_THRESHOLD = 0.55
```

Semantic drift is treated as a weaker signal than an explicitly missing symbol.

---

## 🏗️ Architecture

```text
                 GitHub Pull Request
                         │
                         ▼
              GitHub Actions Workflow
                         │
                         ▼
              Self-Healing Documentation
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
     Source Code                  Markdown Docs
          │                             │
          ▼                             ▼
   code_parser.py                 doc_parser.py
          │                             │
          ▼                             ▼
      Code Chunks                  Doc Sections
          │                             │
          └──────────────┬──────────────┘
                         ▼
                    Embeddings
                         │
                         ▼
                  ChromaDB Store
                         │
                         ▼
              Staleness Detection
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
     Symbol Check    Hash Check    Semantic Drift
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                 Stale Findings
                         │
                         ▼
                 Patch Generator
                         │
               ┌─────────┴─────────┐
               │                   │
               ▼                   ▼
        Rule-Based Patch      LLM-Assisted Patch
               │                   │
               └─────────┬─────────┘
                         ▼
                  Confidence Check
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
        High Confidence        Low Confidence
              │                     │
              ▼                     ▼
       Apply Documentation     Human Review
              │                     │
              └──────────┬──────────┘
                         ▼
                  GitHub Pull Request
```

---

## 🔄 End-to-End Workflow

The complete workflow is:

### Step 1 — Parse the Codebase

The system scans the configured Python source path.

Example:

```yaml
code_path: "src/**/*.py"
```

Python files are parsed into semantic chunks.

---

### Step 2 — Parse Documentation

Markdown files are scanned using:

```yaml
docs_path: "docs/**/*.md"
```

Each Markdown heading becomes a trackable documentation section.

---

### Step 3 — Generate Embeddings

Code chunks are converted into embeddings using:

```text
sentence-transformers/all-MiniLM-L6-v2
```

The vectors are stored locally in ChromaDB.

---

### Step 4 — Link Documentation to Code

Each documentation section is compared against indexed code chunks.

The closest matching code chunk becomes the candidate implementation associated with the documentation.

---

### Step 5 — Detect Staleness

The system checks:

```text
Does the referenced symbol still exist?
            ↓
Has the linked code changed?
            ↓
Has semantic similarity degraded?
```

A `StaleFinding` is generated when a section is considered potentially stale.

Each finding contains information such as:

```python
StaleFinding(
    section_id=...,
    file_path=...,
    heading_path=...,
    reason=...,
    confidence=...,
    linked_chunk_id=...,
    old_code_hash=...,
    new_code_hash=...,
    detail=...
)
```

---

### Step 6 — Generate a Documentation Patch

The system supports two correction strategies.

#### Rule-Based Mode

The default mode requires no LLM API.

The patch is reconstructed using the live code signature and docstring.

Example:

````markdown
```python
load_config(path, strict)
````

Load a YAML config file from disk.

````

This mode is deterministic and requires no external AI service.

---

#### LLM Mode

For more natural documentation, the project can use:

- Groq
- Ollama

The LLM receives the existing documentation section and the corresponding source-code chunk and generates a corrected Markdown body.

---

### Step 7 — Confidence-Based Decision

The generated patch receives a confidence score.

The system combines:

```text
staleness confidence
        +
patch confidence
        ↓
combined confidence
````

The configured threshold determines what happens next.

Default:

```yaml
confidence_threshold: "0.75"
```

If the confidence is high enough:

```text
Documentation → automatically patched
```

Otherwise:

```text
Documentation → flagged for human review
```

---

### Step 8 — Create a Pull Request

When changes are detected, the system:

1. Creates a fix branch
2. Applies documentation changes
3. Updates the manifest
4. Commits the changes
5. Pushes the branch
6. Creates a Pull Request
7. Adds a summary of detected issues
8. Optionally auto-merges when configured

Example branch:

```text
self-healing-docs/fix-123456
```

---

## 🤖 LLM Providers

The project supports three correction modes.

| Provider | API Key | External LLM | Description                               |
| -------- | ------: | -----------: | ----------------------------------------- |
| `none`   |      No |           No | Deterministic rule-based patch generation |
| `groq`   |     Yes |          Yes | Uses Groq's OpenAI-compatible API         |
| `ollama` |      No |        Local | Uses a local Ollama server                |

### Default

```yaml
llm_provider: "none"
```

This allows the Action to operate without an LLM API key.

---

## 🚀 Getting Started

### Prerequisites

For local development:

* Python 3.11+
* Git
* pip
* GitHub repository for Action-based execution

---

## 📦 Installation

Clone the repository:

```bash
git clone https://github.com/YOUR-USERNAME/self-healing-docs.git
cd self-healing-docs
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install testing dependencies:

```bash
pip install pytest
```

---

## 🧪 Run the Test Suite

Run:

```bash
PYTHONPATH=src pytest tests/ -v
```

The project includes a demo repository under:

```text
tests/fixtures/demo_repo/
```

The fixture intentionally contains a documentation/code mismatch.

Documentation references:

```text
load_configuration()
```

while the implementation contains:

```text
load_config()
```

This allows the test suite to verify that the system can identify a removed or renamed symbol.

---

## ⚙️ GitHub Actions Setup

Create:

```text
.github/workflows/doc-health.yml
```

Add:

```yaml
name: Documentation Health Check

on:
  pull_request:
    paths:
      - "src/**/*.py"
      - "docs/**/*.md"

jobs:
  check-docs:
    runs-on: ubuntu-latest

    permissions:
      contents: write
      pull-requests: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Check Documentation
        uses: YOUR-USERNAME/self-healing-docs@v1
        with:
          llm_provider: "none"
          confidence_threshold: "0.75"
          docs_path: "docs/**/*.md"
          code_path: "src/**/*.py"
          auto_merge_high_confidence: "false"
```

Replace:

```text
YOUR-USERNAME/self-healing-docs
```

with the actual GitHub repository containing the Action.

---

## 🔧 Configuration

The Action supports the following inputs.

| Input                        | Default                | Description                                                         |
| ---------------------------- | ---------------------- | ------------------------------------------------------------------- |
| `llm_provider`               | `none`                 | `none`, `groq`, or `ollama`                                         |
| `llm_api_key`                | `""`                   | API key used by the Groq provider                                   |
| `llm_model`                  | `llama-3.1-8b-instant` | Model used for LLM-based patch generation                           |
| `confidence_threshold`       | `0.75`                 | Minimum confidence required for automatic correction                |
| `docs_path`                  | `docs/**/*.md`         | Documentation glob                                                  |
| `code_path`                  | `src/**/*.py`          | Source-code glob                                                    |
| `auto_merge_high_confidence` | `false`                | Automatically merge a fix PR when no low-confidence findings remain |
| `github_token`               | `${{ github.token }}`  | GitHub token used for repository operations                         |

---

## 📤 Action Outputs

The Action exposes:

```text
stale_sections_found
auto_fixed_count
flagged_count
pr_url
```

Example:

```text
stale_sections_found = 3
auto_fixed_count = 1
flagged_count = 2
```

---

## 🗂️ Project Structure

```text
Self-Healing-Technical-Documentation/
│
├── .github/
│
├── examples/
│   └── consumer-workflow.yml
│
├── src/
│   ├── code_parser.py
│   ├── doc_parser.py
│   ├── embeddings.py
│   ├── main.py
│   ├── patch_generator.py
│   ├── pr_ops.py
│   ├── staleness_detector.py
│   └── vectorstore.py
│
├── tests/
│   ├── conftest.py
│   ├── test_parsers.py
│   ├── test_staleness.py
│   └── fixtures/
│       └── demo_repo/
│
├── action.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 🧩 Core Components

### `code_parser.py`

Responsible for converting Python source code into structured semantic chunks.

Uses Python's:

```python
ast
```

module.

Extracts:

* Classes
* Functions
* Methods
* Signatures
* Docstrings
* Source code
* Line numbers
* Content hashes

---

### `doc_parser.py`

Responsible for converting Markdown documents into structured sections.

It tracks:

```text
heading hierarchy
section content
line numbers
referenced code symbols
```

---

### `embeddings.py`

Provides local text embeddings using:

```text
sentence-transformers/all-MiniLM-L6-v2
```

The model is loaded lazily and cached.

---

### `vectorstore.py`

Provides persistent vector storage using:

```text
ChromaDB
```

It supports:

* Code indexing
* Embedding storage
* Similarity search
* Code retrieval by ID

---

### `staleness_detector.py`

Contains the core documentation-health logic.

It checks:

```text
symbol existence
code hash changes
semantic similarity
```

and produces structured `StaleFinding` objects.

---

### `patch_generator.py`

Generates documentation corrections.

It supports:

```text
Rule-based patches
Groq LLM patches
Ollama LLM patches
```

If an LLM call fails, the system falls back to the deterministic rule-based patch generator.

---

### `pr_ops.py`

Handles GitHub-side operations:

```text
create branch
stage changes
commit
push
create Pull Request
post PR comment
optional auto-merge
```

---

### `main.py`

Acts as the application entry point and coordinates the entire workflow:

```text
Parse
  ↓
Index
  ↓
Detect
  ↓
Generate Patch
  ↓
Evaluate Confidence
  ↓
Apply / Review
  ↓
Commit
  ↓
Pull Request
```

---

## 💾 Persistent Manifest

The Action maintains:

```text
.healing-docs/manifest.json
```

The manifest stores the relationship between documentation sections and their previously matched code chunks.

Example structure:

```json
{
  "docs/configuration.md::Configuration > Loading Config": {
    "chunk_id": "src/config.py::load_config",
    "code_hash": "8f3a2d9c1e7b4a21"
  }
}
```

This allows later runs to determine whether the code associated with a documentation section has changed.

---

## 🛡️ Human-in-the-Loop Design

The system intentionally does not treat every detected mismatch as safe to automatically modify.

Instead:

```text
                    Finding
                       │
                       ▼
                Generate Patch
                       │
                       ▼
                Calculate Confidence
                       │
              ┌────────┴────────┐
              │                 │
          High confidence   Low confidence
              │                 │
              ▼                 ▼
        Auto-correct       Human review
```

This reduces the risk of automatically modifying documentation when the system is uncertain about the intended behavior.

---

## 🔐 GitHub Permissions

The example workflow requires:

```yaml
permissions:
  contents: write
  pull-requests: write
```

These permissions are needed because the Action may:

* Create branches
* Push documentation changes
* Create Pull Requests
* Add comments to Pull Requests

If automatic merging is enabled, the repository's GitHub settings and token permissions must also permit the relevant merge operation.

---

## 🐳 Docker

The GitHub Action runs inside a Docker container.

The container is based on:

```dockerfile
python:3.11-slim
```

Git is installed because the Action performs repository operations.

The application entry point is:

```text
src/main.py
```

---

## 🧪 Testing Strategy

The project includes tests for:

### Code Parsing

Verifies that the parser correctly identifies:

* Functions
* Classes
* Methods
* Docstrings
* Content hashes

### Documentation Parsing

Verifies:

* Markdown heading hierarchy
* Section generation
* Code-symbol extraction

### Staleness Detection

Verifies that a renamed function is detected as stale while an accurate documentation section is not incorrectly flagged.

The test suite also provides lightweight stubs for heavy ML dependencies so parser and staleness tests can run without requiring the full embedding/vector stack.

---

## 📊 Evaluating Detection Quality

For real-world evaluation, track:

### True Positives

Stale documentation correctly detected.

### False Positives

Accurate documentation incorrectly marked as stale.

### False Negatives

Actual documentation drift that the system failed to detect.

### Correction Quality

Whether automatically generated documentation accurately describes the current implementation.

A useful evaluation dataset should contain examples of:

```text
function rename
function removal
signature changes
behavior changes
new parameters
changed configuration
unrelated code changes
accurate documentation
semantic documentation drift
```

---

## 🧠 Design Philosophy

The project follows three main principles.

### 1. Code Is the Source of Truth

Documentation should reflect the current implementation rather than an older version of it.

### 2. Confidence Before Automation

Not every detected difference should automatically modify documentation.

High-confidence corrections can be automated, while uncertain cases are surfaced for human review.

### 3. Local-First AI

The default configuration does not require an external LLM.

Embeddings run locally and the default patch generation is deterministic.

LLM providers are optional enhancements rather than mandatory dependencies for the core workflow.

---

## ⚠️ Current Limitations

The current implementation focuses primarily on:

```text
Python source code
+
Markdown documentation
+
GitHub Actions
```

The semantic parser currently extracts Python functions, classes, and methods rather than providing language-independent source-code analysis.

Semantic similarity is also a heuristic. A high similarity score does not guarantee that two pieces of text are logically equivalent.

LLM-generated corrections should therefore still be reviewed when documentation changes are important or behavior is complex.

---

## 🛣️ Possible Future Improvements

Potential extensions include:

* Support for JavaScript/TypeScript
* Support for Java
* Support for additional documentation formats
* Better AST-based signature comparison
* More precise code-to-documentation linking
* Detection of changed function parameters
* API schema comparison
* OpenAPI documentation validation
* Configuration documentation validation
* Test-aware documentation verification
* Improved semantic-drift evaluation
* Web-based documentation health dashboard
* Historical documentation drift analytics
* More granular GitHub PR review comments
* Additional embedding models
* Configurable similarity strategies

---

## 📌 Example Detection

Suppose the documentation contains:

```markdown
## Loading Configuration

Use `load_configuration()` to read the YAML configuration file.
```

But the source code contains:

```python
def load_config(path: str, strict: bool = False) -> dict:
    """Load a YAML config file from disk."""
```

The parser identifies:

```text
Documentation symbol:
load_configuration

Available code symbol:
load_config
```

The system can therefore produce a finding such as:

```text
Reason:
symbol_removed

Confidence:
0.92
```

If a valid code chunk is available for correction, the patch generator can produce an updated documentation section.

---

## 🎯 Why This Project Exists

Traditional documentation checks generally verify formatting, broken links, or spelling.

This project focuses on a different problem:

> **Does the documentation still describe what the code actually does?**

Instead of waiting for developers to discover stale documentation manually, the Action integrates documentation validation directly into the software-development workflow.

```text
Code Change
     ↓
Pull Request
     ↓
Documentation Check
     ↓
Detect Drift
     ↓
Generate Fix
     ↓
Human Review / Automatic Correction
     ↓
Updated Documentation
```

---

## ⭐ Contributing

Contributions are welcome.

A typical contribution workflow is:

```bash
git clone <repository-url>
cd Self-Healing-Technical-Documentation

pip install -r requirements.txt
pip install pytest

PYTHONPATH=src pytest tests/ -v
```

Then create a branch:

```bash
git checkout -b feature/your-feature
```

Make your changes, add tests where appropriate, and open a Pull Request.

---

## 👨‍💻 Project Summary

**Self-Healing Technical Documentation** is a documentation-maintenance GitHub Action that combines static code analysis, semantic search, persistent code fingerprints, confidence-based patch generation, and GitHub automation to keep technical documentation synchronized with evolving Python codebases.

The system is designed around a simple workflow:

```text
Understand the code
        ↓
Understand the documentation
        ↓
Connect documentation to implementation
        ↓
Detect divergence
        ↓
Generate a correction
        ↓
Measure confidence
        ↓
Automate when safe
        ↓
Ask a human when uncertain
```

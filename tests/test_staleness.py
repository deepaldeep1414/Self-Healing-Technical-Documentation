import os
import sys
import shutil
import tempfile
import hashlib
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Stub the embeddings module so this test suite doesn't require sentence-transformers
# / torch to be installed. The real module is used in production; this stub only
# needs to be deterministic so semantic-similarity ordering is stable for the test.
if "embeddings" not in sys.modules:
    _fake = types.ModuleType("embeddings")

    def _fake_vec(text):
        h = hashlib.sha256(text.encode()).digest()
        return [b / 255.0 for b in h[:32]]

    _fake.embed_texts = lambda texts: [_fake_vec(t) for t in texts]
    _fake.embed_one = _fake_vec
    sys.modules["embeddings"] = _fake

from code_parser import parse_codebase          # noqa: E402
from doc_parser import parse_docs                # noqa: E402
from vectorstore import VectorStore              # noqa: E402
from staleness_detector import detect_staleness  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "demo_repo")


def test_renamed_function_flagged_as_stale():
    tmp_persist = tempfile.mkdtemp()
    try:
        code_chunks = parse_codebase(os.path.join(FIXTURE, "src", "*.py"))
        doc_sections = parse_docs(os.path.join(FIXTURE, "docs", "*.md"))
        store = VectorStore(persist_dir=tmp_persist)
        store.index_code_chunks(code_chunks)

        findings = detect_staleness(doc_sections, code_chunks, store, manifest={})
        stale_headings = {f.heading_path for f in findings}

        assert "Configuration > Loading Config" in stale_headings
        loading_finding = next(f for f in findings if f.heading_path == "Configuration > Loading Config")
        assert loading_finding.reason == "symbol_removed"
        assert loading_finding.confidence >= 0.9

        # Accurate section should NOT be flagged
        assert "Configuration > Validating Config" not in stale_headings
    finally:
        shutil.rmtree(tmp_persist, ignore_errors=True)

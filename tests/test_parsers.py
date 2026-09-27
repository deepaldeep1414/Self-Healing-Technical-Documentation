import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from code_parser import parse_codebase          # noqa: E402
from doc_parser import parse_docs                # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "demo_repo")


def test_parse_codebase_finds_function_and_class():
    chunks = parse_codebase(os.path.join(FIXTURE, "src", "*.py"))
    names = {c.name for c in chunks}
    assert "load_config" in names
    assert "ConfigValidator" in names
    assert "ConfigValidator.validate" in names


def test_code_chunk_has_docstring_and_hash():
    chunks = parse_codebase(os.path.join(FIXTURE, "src", "*.py"))
    load_config = next(c for c in chunks if c.name == "load_config")
    assert "Load a YAML config file" in load_config.docstring
    assert len(load_config.content_hash) == 16


def test_parse_docs_splits_sections_by_heading():
    sections = parse_docs(os.path.join(FIXTURE, "docs", "*.md"))
    headings = {s.heading_path for s in sections}
    assert "Configuration" in headings
    assert "Configuration > Loading Config" in headings
    assert "Configuration > Validating Config" in headings


def test_doc_section_extracts_referenced_symbols():
    sections = parse_docs(os.path.join(FIXTURE, "docs", "*.md"))
    loading = next(s for s in sections if s.heading_path == "Configuration > Loading Config")
    assert "load_configuration" in loading.referenced_symbols

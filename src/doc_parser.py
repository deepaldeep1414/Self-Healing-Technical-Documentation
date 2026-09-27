"""Split markdown docs into sections keyed by heading path (e.g. "Configuration > Environment Variables").

Each section records its raw content plus any code-symbol references it mentions
(function/class names, CLI flags, config keys) so it can be linked back to code chunks.
"""
from __future__ import annotations

import glob
import re
from dataclasses import dataclass

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
# Only match backtick tokens that look like an actual function/method *call*
# (end in "()"), e.g. `load_config()` or `ConfigValidator.validate()`.
# Plain field-name mentions like `name` or `version` are NOT code references —
# treating them as such was a real false-positive source caught in testing.
CODE_TOKEN_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_\.]*)\(\)`")


@dataclass
class DocSection:
    section_id: str        # "path/to/file.md::Configuration > Environment Variables"
    file_path: str
    heading_path: str
    content: str
    start_line: int
    end_line: int
    referenced_symbols: list[str]


def _referenced_symbols(text: str) -> list[str]:
    found = set()
    for m in CODE_TOKEN_RE.finditer(text):
        found.add(m.group(1))
    return sorted(found)


def parse_file(file_path: str) -> list[DocSection]:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    sections: list[DocSection] = []
    stack: list[tuple[int, str]] = []  # (level, title)
    current_start = 0
    current_lines: list[str] = []

    def flush(end_line: int):
        if not stack:
            return
        heading_path = " > ".join(t for _, t in stack)
        content = "".join(current_lines).strip()
        sections.append(DocSection(
            section_id=f"{file_path}::{heading_path}",
            file_path=file_path, heading_path=heading_path,
            content=content, start_line=current_start, end_line=end_line,
            referenced_symbols=_referenced_symbols(content),
        ))

    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            flush(i)
            level = len(m.group(1))
            title = m.group(2).strip()
            stack = [s for s in stack if s[0] < level] + [(level, title)]
            current_start = i
            current_lines = []
        else:
            current_lines.append(line)
    flush(len(lines))
    return sections


def parse_docs(docs_glob: str) -> list[DocSection]:
    sections: list[DocSection] = []
    for path in sorted(glob.glob(docs_glob, recursive=True)):
        sections.extend(parse_file(path))
    return sections

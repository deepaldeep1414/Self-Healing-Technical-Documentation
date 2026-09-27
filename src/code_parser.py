"""Parse a Python codebase into semantic chunks: functions, classes, CLI defs, API endpoints.

Each chunk gets a stable identifier: "<file_path>::<qualname>" so it survives
unrelated edits elsewhere in the file and can be diffed run-to-run.
"""
from __future__ import annotations

import ast
import glob
import hashlib
from dataclasses import dataclass, field


@dataclass
class CodeChunk:
    chunk_id: str          # "path/to/file.py::ClassName.method_name"
    file_path: str
    kind: str              # "function" | "class" | "method"
    name: str
    signature: str
    docstring: str
    source: str
    start_line: int
    end_line: int
    content_hash: str = field(default="")

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.source.encode("utf-8")).hexdigest()[:16]


def _signature_of(node) -> str:
    args = []
    for a in node.args.args:
        args.append(a.arg)
    if node.args.vararg:
        args.append("*" + node.args.vararg.arg)
    if node.args.kwarg:
        args.append("**" + node.args.kwarg.arg)
    return f"{node.name}({', '.join(args)})"


def _extract_from_module(tree: ast.Module, source_lines: list[str], file_path: str) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []

    def source_slice(node) -> str:
        start = node.lineno - 1
        end = getattr(node, "end_lineno", node.lineno)
        return "\n".join(source_lines[start:end])

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node) or ""
            chunks.append(CodeChunk(
                chunk_id=f"{file_path}::{node.name}",
                file_path=file_path, kind="class", name=node.name,
                signature=f"class {node.name}", docstring=doc,
                source=source_slice(node), start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
            ))
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    sdoc = ast.get_docstring(sub) or ""
                    chunks.append(CodeChunk(
                        chunk_id=f"{file_path}::{node.name}.{sub.name}",
                        file_path=file_path, kind="method",
                        name=f"{node.name}.{sub.name}", signature=_signature_of(sub),
                        docstring=sdoc, source=source_slice(sub),
                        start_line=sub.lineno, end_line=getattr(sub, "end_lineno", sub.lineno),
                    ))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and isinstance(
            getattr(node, "parent", None), (ast.Module, type(None))
        ):
            # top-level only; nested handled via class branch or skipped
            pass

    # top-level functions (walk misses parent tracking, so do a direct pass)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node) or ""
            chunks.append(CodeChunk(
                chunk_id=f"{file_path}::{node.name}",
                file_path=file_path, kind="function", name=node.name,
                signature=_signature_of(node), docstring=doc,
                source=source_slice(node), start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
            ))
    return chunks


def parse_file(file_path: str) -> list[CodeChunk]:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return []
    return _extract_from_module(tree, source.splitlines(), file_path)


def parse_codebase(code_glob: str) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    for path in sorted(glob.glob(code_glob, recursive=True)):
        chunks.extend(parse_file(path))
    return chunks

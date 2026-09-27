"""Detect stale documentation by comparing doc sections against linked code chunks.

Staleness signals, each contributing to a confidence score (0-1):
  1. Explicit symbol reference in the doc (e.g. `parse_config()`) no longer exists
     in the codebase -> strong signal (renamed/removed function).
  2. The code chunk linked in the manifest changed hash since the last run
     -> code changed, doc content unverified against new behavior.
  3. Semantic similarity between doc section and its best-matching code chunk
     is low -> doc and code have likely diverged in meaning.

No prior manifest (first run) => every section with linked code is treated as
"unverified" rather than stale, since there's nothing to diff against yet.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class StaleFinding:
    section_id: str
    file_path: str
    heading_path: str
    reason: str                 # "symbol_removed" | "code_changed" | "semantic_drift"
    confidence: float           # 0-1, higher = more certain it's stale
    linked_chunk_id: str | None
    old_code_hash: str | None
    new_code_hash: str | None
    detail: str

    def to_dict(self):
        return asdict(self)


SEMANTIC_DRIFT_DISTANCE_THRESHOLD = 0.55  # chroma cosine distance; higher = less similar


def detect_staleness(doc_sections, code_chunks, store, manifest: dict) -> list[StaleFinding]:
    findings: list[StaleFinding] = []
    code_by_name = {}
    for c in code_chunks:
        code_by_name.setdefault(c.name, []).append(c)
        code_by_name.setdefault(c.name.split(".")[-1], []).append(c)

    for section in doc_sections:
        if not section.content.strip():
            continue

        # Signal 1: explicit symbol references that vanished from the codebase
        missing_symbols = [s for s in section.referenced_symbols if s not in code_by_name]
        if section.referenced_symbols and missing_symbols:
            findings.append(StaleFinding(
                section_id=section.section_id, file_path=section.file_path,
                heading_path=section.heading_path, reason="symbol_removed",
                confidence=0.92,
                linked_chunk_id=None, old_code_hash=None, new_code_hash=None,
                detail=f"References {missing_symbols} which no longer exist in code_path.",
            ))
            continue  # strongest signal wins; skip weaker checks for this section

        # Find best semantic match in code for linkage
        related = store.find_related_code(section.content, top_k=1)
        best = related[0] if related else None
        prior = manifest.get(section.section_id)

        if best:
            new_hash = best["metadata"]["content_hash"]
            if prior and prior.get("code_hash") and prior["code_hash"] != new_hash:
                findings.append(StaleFinding(
                    section_id=section.section_id, file_path=section.file_path,
                    heading_path=section.heading_path, reason="code_changed",
                    confidence=0.65,
                    linked_chunk_id=best["chunk_id"], old_code_hash=prior["code_hash"],
                    new_code_hash=new_hash,
                    detail=f"Linked code chunk {best['chunk_id']} changed since last check.",
                ))
            elif best["distance"] > SEMANTIC_DRIFT_DISTANCE_THRESHOLD and prior:
                findings.append(StaleFinding(
                    section_id=section.section_id, file_path=section.file_path,
                    heading_path=section.heading_path, reason="semantic_drift",
                    confidence=0.4,
                    linked_chunk_id=best["chunk_id"], old_code_hash=prior.get("code_hash"),
                    new_code_hash=new_hash,
                    detail=f"Doc/code similarity distance {best['distance']:.2f} exceeds threshold.",
                ))
    return findings


def build_manifest(doc_sections, store) -> dict:
    """Snapshot of doc_section -> best-matching code chunk + its hash, for next run's diff."""
    manifest = {}
    for section in doc_sections:
        related = store.find_related_code(section.content, top_k=1)
        if related:
            manifest[section.section_id] = {
                "chunk_id": related[0]["chunk_id"],
                "code_hash": related[0]["metadata"]["content_hash"],
            }
    return manifest

"""Entry point. Run inside the Action's Docker container.

Args (positional, matching action.yml):
  1 llm_api_key
  2 llm_provider           (none | groq | ollama)
  3 llm_model
  4 confidence_threshold
  5 docs_path
  6 code_path
  7 auto_merge_high_confidence
  8 github_token
"""
from __future__ import annotations

import json
import os
import sys

from code_parser import parse_codebase
from doc_parser import parse_docs
from vectorstore import VectorStore
from staleness_detector import detect_staleness, build_manifest
from patch_generator import generate_patch
import pr_ops

MANIFEST_PATH = ".healing-docs/manifest.json"


def load_manifest() -> dict:
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest: dict) -> None:
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)


def set_output(name: str, value) -> None:
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"::set-output name={name}::{value}")


def main() -> int:
    args = sys.argv[1:] + [""] * 8
    llm_api_key, llm_provider, llm_model, confidence_threshold_s, docs_path, code_path, \
        auto_merge_s, github_token = args[:8]

    confidence_threshold = float(confidence_threshold_s or 0.75)
    auto_merge = str(auto_merge_s).lower() == "true"
    llm_provider = llm_provider or "none"
    repo_full_name = os.environ.get("GITHUB_REPOSITORY", "")
    base_branch = os.environ.get("GITHUB_BASE_REF") or os.environ.get("GITHUB_REF_NAME", "main")

    print(f"[self-healing-docs] parsing code: {code_path}")
    code_chunks = parse_codebase(code_path)
    print(f"[self-healing-docs] parsing docs: {docs_path}")
    doc_sections = parse_docs(docs_path)
    print(f"[self-healing-docs] {len(code_chunks)} code chunks, {len(doc_sections)} doc sections")

    store = VectorStore()
    store.index_code_chunks(code_chunks)

    manifest = load_manifest()
    findings = detect_staleness(doc_sections, code_chunks, store, manifest)
    print(f"[self-healing-docs] {len(findings)} stale sections found")

    sections_by_id = {s.section_id: s for s in doc_sections}
    auto_fixed, flagged = [], []
    changed_files = set()
    fix_notes = []

    for finding in findings:
        section = sections_by_id[finding.section_id]
        code_chunk = store.get_by_id(finding.linked_chunk_id) if finding.linked_chunk_id else None
        patched_body, patch_confidence = generate_patch(
            section, code_chunk, llm_provider, llm_api_key, llm_model,
        )
        combined_confidence = min(finding.confidence, patch_confidence) if code_chunk else finding.confidence * 0.5

        if combined_confidence >= confidence_threshold and code_chunk:
            pr_ops.apply_patch_to_file(section.file_path, section.start_line, section.end_line, patched_body)
            changed_files.add(section.file_path)
            auto_fixed.append((finding, combined_confidence))
            fix_notes.append(f"- ✅ **{finding.heading_path}** (`{section.file_path}`) — {finding.reason}, "
                              f"confidence {combined_confidence:.2f}")
        else:
            flagged.append((finding, combined_confidence))
            fix_notes.append(f"- ⚠️ **{finding.heading_path}** (`{section.file_path}`) — {finding.reason}, "
                              f"confidence {combined_confidence:.2f} (below threshold {confidence_threshold}) — "
                              f"needs human review.")

    new_manifest = build_manifest(doc_sections, store)
    save_manifest(new_manifest)
    changed_files.add(MANIFEST_PATH)

    set_output("stale_sections_found", len(findings))
    set_output("auto_fixed_count", len(auto_fixed))
    set_output("flagged_count", len(flagged))

    verified_count = len(doc_sections) - len(findings)
    summary = (
        f"### 📄 Doc Check Results\n"
        f"{verified_count} sections verified accurate, {len(auto_fixed)} auto-fixed, "
        f"{len(flagged)} flagged for review.\n\n" + "\n".join(fix_notes)
    )

    pr_url = ""
    if repo_full_name and github_token and changed_files and (auto_fixed or True):
        branch_name = f"self-healing-docs/fix-{os.environ.get('GITHUB_RUN_ID', 'local')}"
        pushed = pr_ops.commit_and_push_fixes(
            repo_dir=".", branch_name=branch_name, token=github_token,
            repo_full_name=repo_full_name, changed_files=sorted(changed_files),
            commit_message="docs: auto-fix stale documentation sections",
        )
        if pushed:
            pr_url = pr_ops.open_fix_pr(
                token=github_token, repo_full_name=repo_full_name, branch_name=branch_name,
                base_branch=base_branch, title="docs: auto-fix stale documentation",
                body=summary, auto_merge=auto_merge and not flagged,
            )
            set_output("pr_url", pr_url)

    pr_number = pr_ops.current_pr_number()
    if pr_number and github_token and repo_full_name:
        comment = summary + (f"\n\nFix PR: {pr_url}" if pr_url else "")
        pr_ops.post_pr_comment(github_token, repo_full_name, pr_number, comment)

    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())

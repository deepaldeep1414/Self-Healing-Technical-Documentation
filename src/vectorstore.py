"""File-persisted vector store using ChromaDB (no hosted service, no cost)."""
from __future__ import annotations

import chromadb

from embeddings import embed_texts


class VectorStore:
    def __init__(self, persist_dir: str = ".chroma_cache"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.code_collection = self.client.get_or_create_collection("code_chunks")

    def index_code_chunks(self, chunks) -> None:
        if not chunks:
            return
        ids = [c.chunk_id for c in chunks]
        docs = [f"{c.signature}\n{c.docstring}\n{c.source[:1000]}" for c in chunks]
        metadatas = [{
            "file_path": c.file_path, "kind": c.kind, "name": c.name,
            "content_hash": c.content_hash, "start_line": c.start_line, "end_line": c.end_line,
        } for c in chunks]
        embeddings = embed_texts(docs)
        # upsert in batches to avoid chroma's per-call limits on huge repos
        batch = 128
        for i in range(0, len(ids), batch):
            self.code_collection.upsert(
                ids=ids[i:i + batch], embeddings=embeddings[i:i + batch],
                documents=docs[i:i + batch], metadatas=metadatas[i:i + batch],
            )

    def find_related_code(self, doc_section_text: str, top_k: int = 3):
        if self.code_collection.count() == 0:
            return []
        query_vec = embed_texts([doc_section_text])[0]
        result = self.code_collection.query(query_embeddings=[query_vec], n_results=top_k)
        related = []
        ids = result.get("ids", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]
        for cid, meta, dist in zip(ids, metas, dists):
            related.append({"chunk_id": cid, "metadata": meta, "distance": dist})
        return related

    def get_by_id(self, chunk_id: str):
        result = self.code_collection.get(ids=[chunk_id])
        if not result["ids"]:
            return None
        return {"id": result["ids"][0], "metadata": result["metadatas"][0], "document": result["documents"][0]}

"""
conftest.py — stub out heavy ML dependencies (chromadb, sentence-transformers)
so the test suite runs on Python 3.14 without needing C-extension builds.
"""
import hashlib
import sys
import types


# ---------------------------------------------------------------------------
# Stub: embeddings (sentence-transformers)
# ---------------------------------------------------------------------------
if "embeddings" not in sys.modules:
    _embeddings = types.ModuleType("embeddings")

    def _fake_vec(text: str):
        h = hashlib.sha256(text.encode()).digest()
        return [b / 255.0 for b in h[:32]]

    _embeddings.embed_texts = lambda texts: [_fake_vec(t) for t in texts]
    _embeddings.embed_one = _fake_vec
    sys.modules["embeddings"] = _embeddings


# ---------------------------------------------------------------------------
# Stub: chromadb  (used by vectorstore.py)
# ---------------------------------------------------------------------------
if "chromadb" not in sys.modules:

    class _FakeCollection:
        def __init__(self):
            self._data: dict[str, dict] = {}

        def count(self):
            return len(self._data)

        def upsert(self, ids, embeddings, documents, metadatas):
            for cid, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
                self._data[cid] = {"embedding": emb, "document": doc, "metadata": meta}

        def query(self, query_embeddings, n_results=3):
            # Simple cosine-ish ranking via dot product
            qvec = query_embeddings[0]
            scored = []
            for cid, v in self._data.items():
                dot = sum(a * b for a, b in zip(qvec, v["embedding"]))
                scored.append((dot, cid, v))
            scored.sort(key=lambda x: -x[0])
            top = scored[:n_results]
            return {
                "ids": [[x[1] for x in top]],
                "metadatas": [[x[2]["metadata"] for x in top]],
                "distances": [[1.0 - x[0] for x in top]],
            }

        def get(self, ids):
            found = [cid for cid in ids if cid in self._data]
            return {
                "ids": found,
                "metadatas": [self._data[cid]["metadata"] for cid in found],
                "documents": [self._data[cid]["document"] for cid in found],
            }

    class _FakeClient:
        def __init__(self, path=".chroma_stub"):
            self._collections: dict[str, _FakeCollection] = {}

        def get_or_create_collection(self, name):
            if name not in self._collections:
                self._collections[name] = _FakeCollection()
            return self._collections[name]

    _chromadb = types.ModuleType("chromadb")
    _chromadb.PersistentClient = _FakeClient
    sys.modules["chromadb"] = _chromadb

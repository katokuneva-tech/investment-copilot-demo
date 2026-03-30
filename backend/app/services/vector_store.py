"""Vector store for semantic document search. Uses sentence-transformers + numpy."""
import numpy as np
from typing import Optional


import re as _re


def _split_text(text: str, max_chunk: int = 800) -> list[str]:
    """Split text into semantic chunks.

    Priority: section separators → double newlines (paragraphs) → character limit.
    Preserves financial tables and structured data within chunks.
    """
    chunks = []

    # Split by section separators (===, ---, ##, *** headers in documents)
    sections = _re.split(r'\n(?:={3,}|---+|={3,}\s+.+\s+={3,})\s*', text)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(section) <= max_chunk:
            chunks.append(section)
        else:
            # Split by double newlines (paragraphs)
            paragraphs = _re.split(r'\n\n+', section)
            buffer = ""
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                if len(buffer) + len(para) + 2 <= max_chunk:
                    buffer += ("\n\n" if buffer else "") + para
                else:
                    if buffer:
                        chunks.append(buffer)
                    # If single paragraph is too long, split by newlines
                    if len(para) > max_chunk:
                        lines = para.split("\n")
                        line_buffer = ""
                        for line in lines:
                            if len(line_buffer) + len(line) + 1 <= max_chunk:
                                line_buffer += ("\n" if line_buffer else "") + line
                            else:
                                if line_buffer:
                                    chunks.append(line_buffer)
                                line_buffer = line
                        if line_buffer:
                            buffer = line_buffer
                        else:
                            buffer = ""
                    else:
                        buffer = para
            if buffer:
                chunks.append(buffer)

    return [c for c in chunks if c.strip()]


class VectorStore:
    def __init__(self):
        self._model = None
        self._chunks: list[dict] = []  # {doc_id, doc_name, text, embedding}
        self._available = None

    def _ensure_model(self):
        if self._model is not None:
            return True
        if self._available is False:
            return False
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._available = True
            print("[VECTOR] Model loaded: all-MiniLM-L6-v2")
            return True
        except ImportError:
            self._available = False
            print("[VECTOR] sentence-transformers not installed, falling back to keyword search")
            return False

    def has_data(self) -> bool:
        return len(self._chunks) > 0 and self._available is not False

    def index_document(self, doc_id: str, doc_name: str, text: str, max_chunk: int = 800):
        """Split document into chunks and embed each."""
        if not self._ensure_model():
            return

        # Remove old chunks for this doc
        self._chunks = [c for c in self._chunks if c["doc_id"] != doc_id]

        chunks = _split_text(text, max_chunk)
        for chunk_text in chunks:
            emb = self._model.encode(chunk_text, normalize_embeddings=True)
            self._chunks.append({
                "doc_id": doc_id,
                "doc_name": doc_name,
                "text": chunk_text,
                "embedding": emb,
            })
        print(f"[VECTOR] Indexed {len(chunks)} chunks from {doc_name}")

    def remove_document(self, doc_id: str):
        """Remove all chunks for a document."""
        before = len(self._chunks)
        self._chunks = [c for c in self._chunks if c["doc_id"] != doc_id]
        removed = before - len(self._chunks)
        if removed:
            print(f"[VECTOR] Removed {removed} chunks for doc {doc_id}")

    def search(self, query: str, top_k: int = 10, doc_ids: Optional[list[str]] = None) -> list[str]:
        """Return top_k most relevant text chunks for the query."""
        if not self._ensure_model() or not self._chunks:
            return []

        q_emb = self._model.encode(query, normalize_embeddings=True)

        candidates = self._chunks
        if doc_ids:
            candidates = [c for c in self._chunks if c["doc_id"] in doc_ids]

        if not candidates:
            return []

        # Cosine similarity (embeddings are normalized, so dot product = cosine sim)
        embeddings = np.array([c["embedding"] for c in candidates])
        scores = embeddings @ q_emb

        top_indices = np.argsort(scores)[-top_k:][::-1]
        results = []
        for i in top_indices:
            if scores[i] > 0.15:  # minimum relevance threshold
                c = candidates[i]
                results.append(f"[{c['doc_name']}]\n{c['text']}")
        return results


# Singleton (lazy init — model loads on first use)
vector_store = VectorStore()

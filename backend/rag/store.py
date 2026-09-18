from __future__ import annotations
import hashlib, json, os, threading, time
from datetime import datetime, timezone
from .embeddings import embed_text, cosine


def _content_fingerprint(text: str) -> str:
    """Deterministic SHA-256 fingerprint of the normalised text content."""
    return hashlib.sha256(text.strip().encode('utf-8')).hexdigest()


class JsonVectorStore:
    def __init__(self, path="data/vector_store.json"):
        self.path = str(path)
        self.lock = threading.Lock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.items: list[dict] = []
        # content_fp → item index for O(1) dedup lookup
        self._fp_index: dict[str, int] = {}
        self._load()

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_fp_index(self) -> None:
        """Rebuild the fingerprint index from current items list."""
        self._fp_index = {}
        for i, item in enumerate(self.items):
            fp = item.get('content_fp') or _content_fingerprint(item.get('text', ''))
            self._fp_index[fp] = i

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.items = json.load(f)
            except Exception:
                self.items = []
        self._build_fp_index()

    def _save(self) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False)
        for attempt in range(5):
            try:
                os.replace(tmp, self.path)
                break
            except PermissionError:
                time.sleep(0.05)
                if attempt == 4:
                    # Final fallback for Windows file lock
                    try:
                        with open(self.path, "w", encoding="utf-8") as f:
                            json.dump(self.items, f, ensure_ascii=False)
                        if os.path.exists(tmp):
                            os.remove(tmp)
                    except Exception:
                        pass

    # ── Public API ────────────────────────────────────────────────────────────

    def add(self, text: str, metadata: dict | None = None) -> dict:
        """
        Add a chunk to the store.

        Deduplication is content-fingerprint based:
        • If the exact text already exists, the existing item is returned
          unchanged (even if metadata differs — provenance is stored on
          the first insertion only, which is the canonical source).
        • Thread-safe: the entire check+insert is done under the lock.
        """
        metadata = metadata or {}
        fp = _content_fingerprint(text)
        with self.lock:
            if fp in self._fp_index:
                return self.items[self._fp_index[fp]]
            next_id = max((int(x.get('id', 0)) for x in self.items), default=0) + 1
            item = {
                "id": next_id,
                "text": text,
                "content_fp": fp,
                "embedding": embed_text(text),
                "metadata": metadata,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._fp_index[fp] = len(self.items)
            self.items.append(item)
            self._save()
            return item

    def sync_from_disk(self) -> None:
        """Reload persisted knowledge (multi-process or post-import recovery)."""
        with self.lock:
            self._load()

    def search(self, query: str, limit: int = 5, items: list | None = None) -> list[dict]:
        q = embed_text(query)
        scored = []
        for item in (self.items if items is None else items):
            score = cosine(q, item.get("embedding", []))
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"score": round(score, 4), "text": item["text"], "metadata": item.get("metadata", {})}
            for score, item in scored[:limit]
        ]

    def remove_where(self, predicate) -> int:
        with self.lock:
            before = len(self.items)
            self.items = [x for x in self.items if not predicate(x)]
            if len(self.items) != before:
                self._build_fp_index()
                self._save()
            return before - len(self.items)

    def stats(self) -> dict:
        return {"documents": len(self.items), "storage": self.path}

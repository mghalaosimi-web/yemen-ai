"""
backend/rag/chunker.py
========================
Sentence-aware text chunker that respects Arabic and English sentence
boundaries, word boundaries, and configurable size/overlap constraints.

Strategy:
  1. Split into sentences using Arabic + English punctuation.
  2. Greedily accumulate sentences into chunks up to chunk_size chars.
  3. Back-fill the overlap from the tail of the previous chunk at the
     sentence boundary — never splitting inside a word.
  4. If a single sentence exceeds chunk_size, fall back to word-boundary
     splitting inside that sentence.
"""
from __future__ import annotations
import re

# Sentence-terminal punctuation for Arabic and English.
_SENT_END = re.compile(
    r'(?<=[.!?؟؛…])\s+'          # after standard punctuation + whitespace
    r'|(?<=[\.\!\?؟؛])\n'         # or after punctuation at line end
    r'|\n{2,}',                    # or blank line (paragraph break)
    re.UNICODE,
)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, preserving the terminating punctuation."""
    parts = _SENT_END.split(text)
    out = []
    for p in parts:
        p = p.strip()
        if p:
            out.append(p)
    return out or [text]


def _word_boundary_split(text: str, max_size: int, overlap: int) -> list[str]:
    """
    Fallback: split a very long token-stream at word boundaries.
    Used when a single sentence is longer than max_size.
    """
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for word in words:
        wl = len(word) + (1 if current else 0)
        if length + wl > max_size and current:
            chunks.append(' '.join(current))
            # overlap: reuse last few words
            tail = ' '.join(current)
            if overlap > 0:
                keep: list[str] = []
                kept = 0
                for w in reversed(current):
                    if kept + len(w) + 1 <= overlap:
                        keep.insert(0, w)
                        kept += len(w) + 1
                    else:
                        break
                current = keep
                length = sum(len(w) + 1 for w in keep)
            else:
                current = []
                length = 0
        current.append(word)
        length += len(word) + 1
    if current:
        chunks.append(' '.join(current))
    return chunks or [text]


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[str]:
    """
    Split *text* into overlapping chunks that respect sentence boundaries.

    Parameters
    ----------
    text       : The input text (Arabic, English or mixed).
    chunk_size : Target maximum character count per chunk.
    overlap    : Approximate character overlap between consecutive chunks.

    Returns
    -------
    A list of non-empty string chunks.
    """
    text = ' '.join((text or '').split())   # normalise whitespace
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    sentences = _split_sentences(text)
    chunks: list[str] = []
    current_sents: list[str] = []
    current_len = 0

    for sent in sentences:
        # A single sentence that is too long: fall back to word splitting.
        if len(sent) > chunk_size:
            # Flush current accumulator first.
            if current_sents:
                chunks.append(' '.join(current_sents))
                current_sents, current_len = [], 0
            chunks.extend(_word_boundary_split(sent, chunk_size, overlap))
            continue

        addition = len(sent) + (1 if current_sents else 0)
        if current_len + addition > chunk_size and current_sents:
            # Emit the current chunk.
            chunk_text_val = ' '.join(current_sents)
            chunks.append(chunk_text_val)
            # Build overlap from the tail of the just-emitted chunk.
            overlap_sents: list[str] = []
            overlap_len = 0
            for s in reversed(current_sents):
                if overlap_len + len(s) + 1 <= overlap:
                    overlap_sents.insert(0, s)
                    overlap_len += len(s) + 1
                else:
                    break
            current_sents = overlap_sents
            current_len = overlap_len

        current_sents.append(sent)
        current_len += len(sent) + (1 if len(current_sents) > 1 else 0)

    if current_sents:
        chunks.append(' '.join(current_sents))

    return [c for c in chunks if c.strip()]

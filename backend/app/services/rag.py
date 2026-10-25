"""Grounding corpus loader + retrieval.

Dependency-free TF-IDF over paragraph chunks of data/corpus/*.txt. Deliberately
simple for the hackathon; the interface (`retrieve(query, k)`) is what the
pipelines depend on, so an embedding-based retriever is a drop-in swap.
"""

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..config import DATA_DIR

CORPUS_DIR = DATA_DIR / "corpus"

_TOKEN_RE = re.compile(r"[a-z]+")

_STOPWORDS = frozenset(
    "a an and are as at be by for from has have if in into is it its of on or per "
    "than that the to with within without do does not no this these those".split()
)


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


@dataclass
class Chunk:
    id: str
    source: str
    text: str
    tokens: list[str] = field(repr=False, default_factory=list)


class Retriever:
    def __init__(self, corpus_dir: Path = CORPUS_DIR):
        self.chunks: list[Chunk] = []
        self._df: dict[str, int] = {}
        self._load(corpus_dir)

    def _load(self, corpus_dir: Path):
        for path in sorted(corpus_dir.glob("*.txt")):
            text = path.read_text(encoding="utf-8")
            source = self._extract_source(text) or path.stem
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
            for i, para in enumerate(paragraphs):
                if para.startswith("[PLACEHOLDER") or para.lower().startswith("source:"):
                    continue
                chunk = Chunk(
                    id=f"{path.stem}_chunk_{i}",
                    source=source,
                    text=para,
                    tokens=_tokenize(para),
                )
                self.chunks.append(chunk)
        for chunk in self.chunks:
            for term in set(chunk.tokens):
                self._df[term] = self._df.get(term, 0) + 1

    @staticmethod
    def _extract_source(text: str) -> str | None:
        m = re.search(r"^SOURCE:\s*(.+)$", text, re.MULTILINE)
        return m.group(1).strip() if m else None

    def _idf(self, term: str) -> float:
        n = len(self.chunks)
        return math.log((n + 1) / (self._df.get(term, 0) + 1)) + 1.0

    def _score(self, query_tokens: list[str], chunk: Chunk) -> float:
        if not chunk.tokens:
            return 0.0
        score = 0.0
        for term in set(query_tokens):
            count = chunk.tokens.count(term)
            if count:
                # Log-saturated tf (BM25-style): repeated rare terms win
                # without letting short chunks dominate via length division.
                score += (1.0 + math.log(count)) * self._idf(term)
        return score

    def retrieve(self, query: str, k: int = 4) -> list[Chunk]:
        query_tokens = _tokenize(query)
        scored = [(self._score(query_tokens, c), c) for c in self.chunks]
        scored = [(s, c) for s, c in scored if s > 0]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:k]]

"""Metadata comparison and conservative Crossref candidate selection."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any


def normalize_text(value: str) -> str:
    """Normalize bibliography text for forgiving comparisons."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"[{}\\]", "", value).casefold()
    return " ".join(re.findall(r"\w+", value))


def title_score(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio() * 100


def bibtex_surnames(authors: str) -> set[str]:
    names = set()
    for author in authors.split(" and "):
        parts = [part.strip() for part in author.split(",")]
        surname = parts[0] if len(parts) > 1 else author.strip().split()[-1:]
        if isinstance(surname, list):
            surname = surname[0] if surname else ""
        normalized = normalize_text(surname)
        if normalized:
            names.add(normalized)
    return names


def crossref_surnames(work: dict[str, Any]) -> set[str]:
    return {
        normalized
        for author in work.get("author", [])
        if (normalized := normalize_text(author.get("family", "")))
    }


def work_title(work: dict[str, Any]) -> str:
    titles = work.get("title", [])
    return titles[0] if titles else ""


def publication_year(work: dict[str, Any]) -> str:
    """Extract the first available publication year from Crossref metadata."""
    for field in ("published-print", "published-online", "issued"):
        date_parts = work.get(field, {}).get("date-parts", [])
        if date_parts and date_parts[0]:
            return str(date_parts[0][0])
    return ""


@dataclass(frozen=True)
class Comparison:
    title: float
    author_overlap: int

    @property
    def matches(self) -> bool:
        return self.title >= 75 and self.author_overlap > 0

    def matches_at(self, threshold: float) -> bool:
        """Return whether metadata matches at the requested title threshold."""
        return self.title >= threshold and self.author_overlap > 0


def compare_entry(entry: dict[str, str], work: dict[str, Any]) -> Comparison:
    """Compare a BibTeX entry with Crossref work metadata."""
    title = title_score(entry.get("title", ""), work_title(work))
    authors = bibtex_surnames(entry.get("author", ""))
    overlap = len(authors & crossref_surnames(work)) if authors else 1
    return Comparison(title, overlap)


def select_candidate(
    entry: dict[str, str], candidates: list[dict[str, Any]], threshold: float = 90
) -> dict[str, Any] | None:
    """Return one high-confidence, non-ambiguous Crossref candidate."""
    scored = [
        (compare_entry(entry, candidate), candidate)
        for candidate in candidates
        if candidate.get("DOI") and work_title(candidate)
    ]
    accepted = [
        (comparison, candidate)
        for comparison, candidate in scored
        if comparison.matches_at(threshold)
    ]
    if not accepted:
        return None
    entry_year = entry.get("year", "")

    def score(item: tuple[Comparison, dict[str, Any]]) -> tuple[float, int, bool]:
        comparison, candidate = item
        return (
            comparison.title,
            comparison.author_overlap,
            publication_year(candidate) == entry_year,
        )

    accepted.sort(key=score, reverse=True)
    if len(accepted) > 1 and score(accepted[0]) == score(accepted[1]):
        return None
    return accepted[0][1]

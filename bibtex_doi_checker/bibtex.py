"""BibTeX file and DOI helpers."""

from __future__ import annotations

import re
from pathlib import Path

import bibtexparser
from bibtexparser.bibdatabase import BibDatabase

DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
DOI_URL_PATTERN = re.compile(
    r"^(?:https?://)?(?:dx\.)?doi\.org/(.+)$", re.IGNORECASE
)


def normalize_doi(value: str) -> str | None:
    """Return the bare DOI identifier, or None for an invalid value."""
    candidate = value.strip().strip("<>⟨⟩").strip().replace("\r", "").replace("\n", "")
    match = DOI_URL_PATTERN.match(candidate)
    if match:
        candidate = match.group(1)
    candidate = candidate.rstrip(".,;")
    return candidate if DOI_PATTERN.match(candidate) else None


def read_bibtex(path: Path) -> BibDatabase:
    """Load a BibTeX database from a file."""
    with path.open(encoding="utf-8") as source:
        return bibtexparser.load(source)


def write_bibtex(database: BibDatabase, path: Path) -> None:
    """Write a BibTeX database to a file."""
    with path.open("w", encoding="utf-8") as destination:
        bibtexparser.dump(database, destination)

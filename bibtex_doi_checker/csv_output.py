"""CSV export helpers shared by DOI command-line tools."""

from __future__ import annotations

import csv
from pathlib import Path

from .bibtex import normalize_doi

FIELDS = ["bibtex_key", "doi", "title", "authors", "doi_url"]


def bibtex_rows(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    """Create CSV rows from BibTeX entries."""
    return [
        row(
            entry.get("ID", ""),
            entry.get("doi", ""),
            entry.get("title", ""),
            entry.get("author", ""),
        )
        for entry in entries
    ]


def row(bibtex_key: str, doi: str, title: str, authors: str) -> dict[str, str]:
    """Create one CSV row, including a resolver URL for valid DOI values."""
    normalized = normalize_doi(doi)
    return {
        "bibtex_key": bibtex_key,
        "doi": normalized or doi,
        "title": title,
        "authors": authors,
        "doi_url": f"https://doi.org/{normalized}" if normalized else "",
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write DOI data to a UTF-8 CSV file."""
    with path.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

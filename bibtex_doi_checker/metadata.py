"""Metadata provider routing by DOI type."""

from __future__ import annotations

from typing import Any

from .arxiv import arxiv_id_from_doi, get_work as get_arxiv_work
from .crossref import get_work as get_crossref_work


def resolve_work(doi: str, timeout: float) -> dict[str, Any]:
    """Resolve arXiv DOI metadata with arXiv; use Crossref otherwise."""
    return get_arxiv_work(doi, timeout) if arxiv_id_from_doi(doi) else get_crossref_work(doi, timeout)

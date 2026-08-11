"""Command-line tool for checking DOI references in PDF files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .arxiv import ArxivError
from .bibtex import normalize_doi
from .crossref import CrossrefError
from .metadata import resolve_work

DOI_REFERENCE_PATTERN = re.compile(
    r"(?:https?://(?:dx\.)?doi\.org/)?10\.\d{1,12}/[^\s<>{}\[\]\"']+",
    re.IGNORECASE,
)
REFERENCES_HEADING_PATTERN = re.compile(r"(?im)^\s*(?:references|bibliography)\s*$")
NUMBERED_REFERENCE_PATTERN = re.compile(r"(?m)^\s*(?:\[\d+\]|\d+[.)])\s+")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check DOI references in a PDF and report invalid occurrences by page."
    )
    parser.add_argument("input", type=Path, help="input PDF file")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show parsed DOI values and lookup attempts"
    )
    parser.add_argument("--timeout", type=float, default=15, help="metadata lookup timeout in seconds")
    return parser


def _page_texts(reader: PdfReader) -> list[str]:
    return [
        re.sub(r"(10\.\d{1,12}/\S*)\s*\n\s*(?=\d)", r"\1", page.extract_text() or "")
        for page in reader.pages
    ]


def _doi_occurrences(page_texts: list[str]) -> list[tuple[int, str]]:
    occurrences = []
    for page_number, text in enumerate(page_texts, start=1):
        occurrences.extend((page_number, match.group()) for match in DOI_REFERENCE_PATTERN.finditer(text))
    return occurrences


def _reference_doi_stats(page_texts: list[str]) -> tuple[int, int] | None:
    """Estimate numbered references that do not contain a DOI."""
    references = REFERENCES_HEADING_PATTERN.search("\n".join(page_texts))
    if not references:
        return None
    text = "\n".join(page_texts)[references.end() :]
    starts = list(NUMBERED_REFERENCE_PATTERN.finditer(text))
    if not starts:
        return None
    blocks = [
        text[start.end() : starts[index + 1].start() if index + 1 < len(starts) else None]
        for index, start in enumerate(starts)
    ]
    without_doi = sum(not DOI_REFERENCE_PATTERN.search(block) for block in blocks)
    return len(blocks), without_doi


def check_main() -> int:
    args = _parser().parse_args()
    try:
        reader = PdfReader(args.input)
    except (FileNotFoundError, PdfReadError) as error:
        _parser().error(str(error))

    page_texts = _page_texts(reader)
    occurrences = _doi_occurrences(page_texts)
    results: dict[str, str | None] = {}
    invalid = 0
    for page_number, raw_doi in occurrences:
        doi = normalize_doi(raw_doi)
        if args.verbose:
            print(f"\033[1;36mPARSED: Page {page_number}: {doi or raw_doi}\033[0m")
        if not doi:
            print(f"Page {page_number}: invalid DOI: {raw_doi}")
            invalid += 1
            continue
        if doi not in results:
            if args.verbose:
                print(f"\033[1;34mTESTING: {doi}\033[0m")
            try:
                resolve_work(doi, args.timeout)
                results[doi] = None
            except (ArxivError, CrossrefError) as error:
                results[doi] = str(error)
        if results[doi]:
            print(f"Page {page_number}: invalid DOI: {doi} ({results[doi]})")
            invalid += 1

    print(
        f"Checked {len(occurrences)} DOI occurrence(s) on {len(reader.pages)} page(s); "
        f"found {invalid} invalid occurrence(s)."
    )
    reference_stats = _reference_doi_stats(page_texts)
    if reference_stats:
        references, without_doi = reference_stats
        print(f"Tentative references without DOI: {without_doi} of {references}.")
    else:
        print("Tentative references without DOI: unavailable (no numbered References section found).")
    return 1 if invalid else 0

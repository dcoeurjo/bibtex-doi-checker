"""Command-line interfaces for BibTeX DOI tools."""

from __future__ import annotations

import argparse
from pathlib import Path

from .arxiv import (
    ArxivError,
    arxiv_id_from_doi,
    get_work as get_arxiv_work,
    search_works as search_arxiv_works,
)
from .bibtex import normalize_doi, read_bibtex, write_bibtex
from .crossref import CrossrefError, get_work, search_works
from .csv_output import bibtex_rows, write_csv
from .matching import Comparison, compare_entry, select_candidate, work_title


def _threshold(value: str) -> float:
    try:
        threshold = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("threshold must be a number") from error
    if not 0 <= threshold <= 100:
        raise argparse.ArgumentTypeError("threshold must be between 0 and 100")
    return threshold


def _parser(
    description: str,
    output: bool = False,
    verbose: bool = False,
    threshold: float | None = None,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("input", type=Path, help="input BibTeX file")
    if output:
        parser.add_argument("output", type=Path, help="output BibTeX file")
    if verbose:
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="show color diagnostics for invalid DOI values and metadata mismatches",
        )
    if threshold is not None:
        parser.add_argument(
            "--threshold",
            type=_threshold,
            default=threshold,
            metavar="PERCENT",
            help=f"minimum fuzzy title similarity percentage (default: {threshold:.0f})",
        )
    parser.add_argument("--csv", type=Path, metavar="OUTPUT.csv", help="write DOI data to CSV")
    parser.add_argument("--timeout", type=float, default=15, help="Crossref timeout in seconds")
    return parser


def _entry_name(entry: dict[str, str]) -> str:
    return entry.get("ID", "<unknown>")


def _get_work(doi: str, timeout: float) -> dict:
    """Resolve arXiv DOI metadata with arXiv; use Crossref otherwise."""
    return get_arxiv_work(doi, timeout) if arxiv_id_from_doi(doi) else get_work(doi, timeout)


def _metadata_authors(work: dict) -> str:
    return " and ".join(
        author.get("family", author.get("name", ""))
        for author in work.get("author", [])
        if author.get("family", author.get("name", ""))
    ) or "<missing>"


def _print_invalid_doi(entry: dict[str, str], value: str) -> None:
    print(f"\033[1;31mINVALID DOI: {_entry_name(entry)}\033[0m")
    print(f"  DOI field: {value or '<empty>'}")
    print(f"  Title: {entry.get('title', '<missing>')}")
    print(f"  Authors: {entry.get('author', '<missing>')}")


def _print_mismatch(
    entry: dict[str, str], doi: str, work: dict, comparison: Comparison
) -> None:
    print(f"\033[1;33mMETADATA MISMATCH: {_entry_name(entry)}\033[0m")
    print(f"  DOI: {doi}")
    print(f"  {'Field':<10} {'BibTeX entry':<38} Retrieved metadata")
    print(f"  {'-' * 10} {'-' * 38} {'-' * 24}")
    print(f"  {'Title':<10} {entry.get('title', '<missing>'):<38} {work_title(work) or '<missing>'}")
    print(f"  {'Authors':<10} {entry.get('author', '<missing>'):<38} {_metadata_authors(work)}")
    print(f"  Title similarity: {comparison.title:.0f}%")
    print(f"  Author overlap: {comparison.author_overlap}")


def _print_checking_entry(entry: dict[str, str]) -> None:
    print(f"\033[1;36mCHECKING: {_entry_name(entry)}\033[0m")
    print(f"  DOI field: {entry.get('doi', '<missing>')}")
    print(f"  Title: {entry.get('title', '<missing>')}")
    print(f"  Authors: {entry.get('author', '<missing>')}")


def _print_fixer_details(entry: dict[str, str], heading: str, color: str, threshold: float) -> None:
    print(f"\033[1;{color}m{heading}: {_entry_name(entry)}\033[0m")
    print(f"  Title: {entry.get('title', '<missing>')}")
    print(f"  Authors: {entry.get('author', '<missing>')}")
    print(f"  Title similarity threshold: {threshold:.0f}%")


def _choose_candidate(
    entry: dict[str, str], crossref_candidate: dict, arxiv_candidate: dict
) -> dict | None:
    print(f"\033[1;33mMULTIPLE SOURCES: {_entry_name(entry)}\033[0m")
    print(f"  [c] Crossref: {crossref_candidate['DOI']} - {work_title(crossref_candidate)}")
    print(f"  [a] arXiv: {arxiv_candidate['DOI']} - {work_title(arxiv_candidate)}")
    try:
        choice = input("Choose DOI source [c/a, Enter to skip]: ").strip().casefold()
    except EOFError:
        choice = ""
    if choice == "c":
        return crossref_candidate
    if choice == "a":
        return arxiv_candidate
    print(f"{_entry_name(entry)}: no DOI selected")
    return None


def check_main() -> int:
    args = _parser(
        "Check DOI metadata against BibTeX entries.", verbose=True, threshold=75
    ).parse_args()
    database = read_bibtex(args.input)
    problems = 0
    entries_with_doi = 0
    valid_dois = 0
    for entry in database.entries:
        value = entry.get("doi")
        if value is None:
            continue
        entries_with_doi += 1
        if args.verbose:
            _print_checking_entry(entry)
        doi = normalize_doi(value)
        if not doi:
            print(f"{_entry_name(entry)}: invalid DOI: {value}")
            if args.verbose:
                _print_invalid_doi(entry, value)
            problems += 1
            continue
        valid_dois += 1
        try:
            work = _get_work(doi, args.timeout)
            comparison = compare_entry(entry, work)
        except (ArxivError, CrossrefError) as error:
            print(f"{_entry_name(entry)}: lookup failed for {doi}: {error}")
            problems += 1
            continue
        if not comparison.matches_at(args.threshold):
            print(
                f"{_entry_name(entry)}: metadata mismatch for {doi} "
                f"(title {comparison.title:.0f}%, author overlap {comparison.author_overlap})"
            )
            if args.verbose:
                _print_mismatch(entry, doi, work, comparison)
            problems += 1
    print(
        "Statistics: "
        f"{len(database.entries)} total entries; "
        f"{entries_with_doi} with DOI; "
        f"{valid_dois} with valid DOI; "
        f"{problems} problem(s)."
    )
    if args.csv:
        write_csv(args.csv, bibtex_rows(database.entries))
    return 1 if problems else 0


def fix_main() -> int:
    args = _parser(
        "Add missing high-confidence DOIs using Crossref.",
        output=True,
        verbose=True,
        threshold=90,
    ).parse_args()
    database = read_bibtex(args.input)
    added = failed = skipped = 0
    for entry in database.entries:
        if entry.get("doi"):
            skipped += 1
            continue
        title = entry.get("title")
        if not title:
            print(f"{_entry_name(entry)}: skipped (no title)")
            if args.verbose:
                _print_fixer_details(entry, "SKIPPED", "33", args.threshold)
            failed += 1
            continue
        if args.verbose:
            _print_fixer_details(entry, "SEARCHING", "36", args.threshold)
        crossref_candidate = arxiv_candidate = None
        try:
            crossref_candidate = select_candidate(
                entry,
                search_works(title, entry.get("author", ""), args.timeout),
                args.threshold,
            )
        except CrossrefError as error:
            print(f"{_entry_name(entry)}: search failed: {error}")
        try:
            arxiv_candidate = select_candidate(
                entry, search_arxiv_works(title, args.timeout), args.threshold
            )
        except ArxivError as error:
            print(f"{_entry_name(entry)}: arXiv search failed: {error}")
        if crossref_candidate and arxiv_candidate:
            candidate = _choose_candidate(entry, crossref_candidate, arxiv_candidate)
        else:
            candidate = crossref_candidate or arxiv_candidate
        if not candidate:
            if not (crossref_candidate and arxiv_candidate):
                print(f"{_entry_name(entry)}: no confident DOI found")
                if args.verbose:
                    _print_fixer_details(entry, "NO CONFIDENT DOI", "33", args.threshold)
            failed += 1
            continue
        entry["doi"] = candidate["DOI"]
        print(f"{_entry_name(entry)}: added {candidate['DOI']}")
        if args.verbose:
            _print_fixer_details(entry, "DOI ADDED", "32", args.threshold)
        added += 1
    write_bibtex(database, args.output)
    if args.csv:
        write_csv(args.csv, bibtex_rows(database.entries))
    print(
        f"Added {added} DOI(s); "
        f"skipped {skipped} entry(s) with an existing DOI; "
        f"{failed} entry(s) unchanged."
    )
    return 1 if failed else 0


def clean_main() -> int:
    args = _parser("Normalize DOI fields to bare DOI identifiers.", output=True).parse_args()
    database = read_bibtex(args.input)
    changed = invalid = 0
    for entry in database.entries:
        value = entry.get("doi")
        if not value:
            continue
        doi = normalize_doi(value)
        if not doi:
            print(f"{_entry_name(entry)}: invalid DOI left unchanged: {value}")
            invalid += 1
            continue
        if doi != value:
            entry["doi"] = doi
            changed += 1
    write_bibtex(database, args.output)
    if args.csv:
        write_csv(args.csv, bibtex_rows(database.entries))
    print(f"Cleaned {changed} DOI(s); {invalid} invalid DOI(s) left unchanged.")
    return 1 if invalid else 0

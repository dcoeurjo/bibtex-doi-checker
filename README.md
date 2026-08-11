# bibtex/pdf-doi-checker

A [digital object identifier (DOI)](https://en.wikipedia.org/wiki/Digital_object_identifier)
is a persistent identifier for scholarly publications and other digital objects.

Small command-line tools for checking, completing, and cleaning DOI
fields in BibTeX files and PDF. They use the
[Crossref REST API](https://api.crossref.org) for paper metadata, except arXiv
DOIs, which are resolved through the [arXiv API](https://info.arxiv.org/help/api/).
The suite includes four commands: BibTeX checking, fixing, and cleaning, plus
PDF reference checking.

For checking references from a PDF (not only from DOI keys as done here), see the 
[reference_check](https://github.com/rubenwiersma/reference_check) project.

The [documentation site](https://dcoeurjo.github.io/bibtex-doi-checker/) gives a visual overview
and copyable command examples.

## Installation

Install from a clone:

```console
python -m pip install .
```

For development, install the test extra:

```console
python -m pip install -e '.[test]'
```

## Commands

| Command | Purpose | Writes a file |
| --- | --- | --- |
| `bibtex-doi-checker INPUT.bib` | Check DOI/title/author metadata against Crossref. | No |
| `bibtex-doi-fixer INPUT.bib OUTPUT.bib` | Add high-confidence DOIs to entries without one. | Yes |
| `bibtex-doi-cleaner INPUT.bib OUTPUT.bib` | Replace DOI resolver URLs with bare DOI identifiers. | Yes |
| `pdf-doi-checker INPUT.pdf` | Validate DOI references and report invalid occurrences by page. | No |

All commands accept `--csv OUTPUT.csv` to write DOI data with the columns
`bibtex_key`, `doi`, `title`, `authors`, and `doi_url`. PDF rows leave the
BibTeX-specific fields blank because PDF references do not contain BibTeX keys.

### Check DOI metadata

```console
bibtex-doi-checker --threshold 80 examples/check-dois.bib
```

The checker looks up each DOI and compares its title and author surnames with
the BibTeX entry. Standard DOIs are resolved through Crossref; arXiv DOI
values such as `10.48550/arXiv.1706.03762` are resolved through the arXiv API.
It tolerates minor formatting differences and reports invalid DOI values,
lookup errors, and likely mismatches. It exits with status 1 if any problem is
found. Its final statistics line reports the total number of BibTeX entries,
entries with a DOI field, and entries with a syntactically valid DOI.

Pass `-v` or `--verbose` to show colored terminal diagnostics for each invalid
DOI and metadata mismatch. The diagnostic shows the entry key, BibTeX title
and authors beside the resolved metadata in a two-column view, plus the
title/author comparison scores.
Use `--threshold PERCENT` to set the minimum fuzzy title similarity; the
checker default is 75.

### Add missing DOIs

```console
bibtex-doi-fixer -v --threshold 92 examples/missing-dois.bib references-with-dois.bib
```

The fixer searches Crossref and arXiv using the title and author fields. It
adds a DOI only when one candidate is a clear, high-confidence match; existing
DOI fields are never changed. If both sources produce a candidate, it presents
both DOI values and asks which source to use. It always writes the output file
and exits with status 1 when one or more entries could not be updated. Its
final statistics line also reports entries skipped because they already have a
DOI.
When otherwise identical candidates are returned, a matching BibTeX year is
used to select the correct record.

Use `-v` or `--verbose` to show colored search, skipped-entry, and
high-confidence-match details. Use `--threshold PERCENT` to set the minimum
fuzzy title similarity used to add a DOI; the conservative default is 90.

### Clean DOI fields

```console
bibtex-doi-cleaner examples/doi-urls.bib references-clean.bib
```

The cleaner turns resolver URLs such as
`https://doi.org/10.1145/324133.324140` into `10.1145/324133.324140`. It
leaves invalid DOI values unchanged, writes the output file, and exits with
status 1 when it finds one.

All commands accept `--timeout SECONDS` for Crossref requests. Fuzzy matching
is used only by the checker and fixer; the cleaner therefore has no threshold
option. The fixer and cleaner require an output path, so input files are not
overwritten by default.

### Check DOI references in a PDF

```console
pdf-doi-checker article.pdf
```

The PDF checker extracts DOI shortcodes and `doi.org` URLs from each text page.
It validates normal DOI values through Crossref and arXiv DOI values through
the arXiv API. Every invalid DOI occurrence is reported with its one-based PDF
page number; repeated references are reported on every page where they occur.
Scanned PDFs must contain selectable text, not only images.
Pass `-v` or `--verbose` to print each parsed DOI and each unique DOI lookup.
When it finds a `References` or `Bibliography` heading followed by numbered
entries, it also reports a tentative count of references without a DOI.

## Example files

The [`examples/`](examples) directory contains small BibTeX files for trying
each command:

- `check-dois.bib` includes a matching entry, a likely mismatch, and an
  invalid DOI.
- `missing-dois.bib` contains a Crossref-resolvable entry without a DOI field
  for the fixer.
- `doi-urls.bib` contains bare and URL-form DOI values for the cleaner.
- `Stochastic-Processes.pdf` is a small PDF with valid DOI references for the
  PDF checker.

## Development

```console
python -m pytest -q
```

## Contributing

Feel free to report any bugs or feature requests by opening an issue. Pull requests are welcome. If you have bibtex entries or PDF files that are not handled correctly, please include them in the issue or pull request.

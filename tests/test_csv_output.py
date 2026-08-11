import csv
import sys

from bibtex_doi_checker import cli, pdf_cli


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def test_checker_writes_bibtex_csv(tmp_path, monkeypatch):
    source = tmp_path / "input.bib"
    report = tmp_path / "report.csv"
    source.write_text(
        """@article{sample,
  title = {A Simple Study},
  author = {Doe, Jane},
  doi = {https://doi.org/10.1000/sample}
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys, "argv", ["bibtex-doi-checker", str(source), "--csv", str(report)]
    )
    monkeypatch.setattr(
        cli,
        "_get_work",
        lambda doi, timeout: {
            "title": ["A Simple Study"],
            "author": [{"family": "Doe"}],
        },
    )

    assert cli.check_main() == 0
    assert read_rows(report) == [
        {
            "bibtex_key": "sample",
            "doi": "10.1000/sample",
            "title": "A Simple Study",
            "authors": "Doe, Jane",
            "doi_url": "https://doi.org/10.1000/sample",
        }
    ]


def test_fixer_and_cleaner_write_updated_bibtex_csv(tmp_path, monkeypatch):
    source = tmp_path / "input.bib"
    fixed = tmp_path / "fixed.bib"
    fixed_report = tmp_path / "fixed.csv"
    cleaned = tmp_path / "cleaned.bib"
    cleaned_report = tmp_path / "cleaned.csv"
    source.write_text(
        """@article{sample,
  title = {A Simple Study},
  author = {Doe, Jane}
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["bibtex-doi-fixer", str(source), str(fixed), "--csv", str(fixed_report)],
    )
    monkeypatch.setattr(
        cli,
        "search_works",
        lambda title, author, timeout: [
            {
                "DOI": "10.1000/found",
                "title": ["A Simple Study"],
                "author": [{"family": "Doe"}],
            }
        ],
    )
    monkeypatch.setattr(cli, "search_arxiv_works", lambda title, timeout: [])

    assert cli.fix_main() == 0
    assert read_rows(fixed_report)[0]["doi"] == "10.1000/found"

    monkeypatch.setattr(
        sys,
        "argv",
        ["bibtex-doi-cleaner", str(fixed), str(cleaned), "--csv", str(cleaned_report)],
    )
    assert cli.clean_main() == 0
    assert read_rows(cleaned_report)[0]["doi_url"] == "https://doi.org/10.1000/found"


def test_pdf_checker_writes_doi_csv(tmp_path, monkeypatch):
    report = tmp_path / "report.csv"

    class Page:
        def extract_text(self):
            return "Reference: https://doi.org/10.1000/example."

    class Reader:
        pages = [Page()]

    monkeypatch.setattr(pdf_cli, "PdfReader", lambda path: Reader())
    monkeypatch.setattr(
        sys, "argv", ["pdf-doi-checker", "article.pdf", "--csv", str(report)]
    )
    monkeypatch.setattr(pdf_cli, "resolve_work", lambda doi, timeout: None)

    assert pdf_cli.check_main() == 0
    assert read_rows(report) == [
        {
            "bibtex_key": "",
            "doi": "10.1000/example",
            "title": "",
            "authors": "",
            "doi_url": "https://doi.org/10.1000/example",
        }
    ]

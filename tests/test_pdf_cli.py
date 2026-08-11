import sys

from bibtex_doi_checker import pdf_cli


def test_pdf_checker_reports_invalid_doi_page_numbers(monkeypatch, tmp_path, capsys):
    class Page:
        def __init__(self, text):
            self.text = text

        def extract_text(self):
            return self.text

    class Reader:
        pages = [
            Page("References\\nhttps://doi.org/10.1000/good."),
            Page("Bad reference: 10.1000/missing"),
            Page("Repeated bad reference: https://doi.org/10.1000/missing"),
        ]

    monkeypatch.setattr(pdf_cli, "PdfReader", lambda path: Reader())
    monkeypatch.setattr(sys, "argv", ["pdf-doi-checker", str(tmp_path / "article.pdf")])

    def resolve(doi, timeout):
        if doi == "10.1000/missing":
            raise pdf_cli.CrossrefError("HTTP 404")

    monkeypatch.setattr(pdf_cli, "resolve_work", resolve)

    assert pdf_cli.check_main() == 1
    output = capsys.readouterr().out
    assert "Page 2: invalid DOI: 10.1000/missing (HTTP 404)" in output
    assert "Page 3: invalid DOI: 10.1000/missing (HTTP 404)" in output
    assert "Checked 3 DOI occurrence(s) on 3 page(s); found 2 invalid occurrence(s)." in output


def test_pdf_checker_reports_syntactically_invalid_dois(monkeypatch, tmp_path, capsys):
    class Page:
        def extract_text(self):
            return "10.123/too-short"

    class Reader:
        pages = [Page()]

    monkeypatch.setattr(pdf_cli, "PdfReader", lambda path: Reader())
    monkeypatch.setattr(sys, "argv", ["pdf-doi-checker", str(tmp_path / "article.pdf")])

    assert pdf_cli.check_main() == 1
    assert "Page 1: invalid DOI: 10.123/too-short" in capsys.readouterr().out


def test_pdf_checker_joins_line_wrapped_dois(monkeypatch, tmp_path, capsys):
    class Page:
        def extract_text(self):
            return "Reference: 10.1109/VLSM.\n2001.938899"

    class Reader:
        pages = [Page()]

    resolved = []
    monkeypatch.setattr(pdf_cli, "PdfReader", lambda path: Reader())
    monkeypatch.setattr(
        sys, "argv", ["pdf-doi-checker", "-v", str(tmp_path / "article.pdf")]
    )
    monkeypatch.setattr(
        pdf_cli, "resolve_work", lambda doi, timeout: resolved.append(doi)
    )

    assert pdf_cli.check_main() == 0
    assert resolved == ["10.1109/VLSM.2001.938899"]
    output = capsys.readouterr().out
    assert "\033[1;36mPARSED: Page 1: 10.1109/VLSM.2001.938899\033[0m" in output
    assert "\033[1;34mTESTING: 10.1109/VLSM.2001.938899\033[0m" in output

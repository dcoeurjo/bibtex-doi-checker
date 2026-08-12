import sys

import pytest

from bibtex_doi_checker import cli


def write_input(path, doi="https://doi.org/10.1000/sample"):
    path.write_text(
        f"""@article{{sample,
  title = {{A Simple Study}},
  author = {{Doe, Jane}},
  doi = {{{doi}}}
}}
""",
        encoding="utf-8",
    )


def test_cleaner_writes_bare_doi(tmp_path, monkeypatch, capsys):
    source = tmp_path / "input.bib"
    output = tmp_path / "output.bib"
    write_input(source)
    monkeypatch.setattr(sys, "argv", ["bibtex-doi-cleaner", str(source), str(output)])

    assert cli.clean_main() == 0
    assert "doi = {10.1000/sample}" in output.read_text(encoding="utf-8")
    output = capsys.readouterr().out
    assert "Cleaned 1 DOI(s)" in output
    assert "Progress [" in output
    assert "valid DOI: 1 | invalid DOI: 0 | no DOI: 0" in output


def test_checker_reports_crossref_mismatch(tmp_path, monkeypatch, capsys):
    source = tmp_path / "input.bib"
    write_input(source, "10.1000/sample")
    monkeypatch.setattr(sys, "argv", ["bibtex-doi-checker", str(source)])
    monkeypatch.setattr(
        cli,
        "_get_work",
        lambda doi, timeout: {
            "title": ["An Unrelated Paper"],
            "author": [{"family": "Other"}],
        },
    )

    assert cli.check_main() == 1
    output = capsys.readouterr().out
    assert "sample: metadata mismatch" in output
    assert "Statistics: 1 total entries; 1 with DOI; 1 with valid DOI; 1 problem(s)." in output


def test_checker_reports_entry_and_doi_statistics(tmp_path, monkeypatch, capsys):
    source = tmp_path / "input.bib"
    source.write_text(
        """@article{valid,
  title = {A Valid Entry},
  author = {Doe, Jane},
  doi = {10.1000/valid}
}
@article{invalid,
  title = {An Invalid Entry},
  doi = {not-a-doi}
}
@article{missing,
  title = {A Missing DOI}
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["bibtex-doi-checker", str(source)])
    monkeypatch.setattr(
        cli,
        "_get_work",
        lambda doi, timeout: {"title": ["A Valid Entry"], "author": [{"family": "Doe"}]},
    )

    assert cli.check_main() == 1
    assert "Statistics: 3 total entries; 2 with DOI; 1 with valid DOI; 1 problem(s)." in (
        capsys.readouterr().out
    )


def test_checker_verbose_output_shows_invalid_and_mismatched_metadata(
    tmp_path, monkeypatch, capsys
):
    source = tmp_path / "input.bib"
    source.write_text(
        """@article{mismatch,
  title = {A BibTeX Title},
  author = {Doe, Jane},
  doi = {10.1000/mismatch}
}
@article{invalid,
  title = {An Invalid Entry},
  author = {Example, Alex},
  doi = {not-a-doi}
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["bibtex-doi-checker", "-v", str(source)])
    monkeypatch.setattr(
        cli,
        "_get_work",
        lambda doi, timeout: {
            "title": ["A Different Resolved Title"],
            "author": [{"family": "Other"}],
        },
    )

    assert cli.check_main() == 1
    output = capsys.readouterr().out
    assert "\033[1;36mCHECKING: mismatch\033[0m" in output
    assert "DOI field: 10.1000/mismatch" in output
    assert "\033[1;33mMETADATA MISMATCH: mismatch\033[0m" in output
    assert "Field      BibTeX entry" in output
    assert "Title      A BibTeX Title" in output
    assert "A Different Resolved Title" in output
    assert "\033[1;31mINVALID DOI: invalid\033[0m" in output
    assert "DOI field: not-a-doi" in output


def test_checker_resolves_arxiv_doi_with_arxiv_client(monkeypatch):
    monkeypatch.setattr(cli, "get_work", lambda doi, timeout: pytest.fail("used Crossref"))
    monkeypatch.setattr(
        cli,
        "get_arxiv_work",
        lambda doi, timeout: {"title": ["Attention Is All You Need"], "author": []},
    )

    assert cli._get_work("10.48550/arXiv.1706.03762", 10)["title"] == [
        "Attention Is All You Need"
    ]


def test_fixer_verbose_output_shows_search_details(tmp_path, monkeypatch, capsys):
    source = tmp_path / "input.bib"
    output = tmp_path / "output.bib"
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
        ["bibtex-doi-fixer", "-v", "--threshold", "95", str(source), str(output)],
    )
    monkeypatch.setattr(cli, "search_works", lambda title, author, timeout: [])
    monkeypatch.setattr(cli, "search_arxiv_works", lambda title, timeout: [])

    assert cli.fix_main() == 1
    output_text = capsys.readouterr().out
    assert "\033[1;36mSEARCHING: sample\033[0m" in output_text
    assert "\033[1;33mNO CONFIDENT DOI: sample\033[0m" in output_text
    assert "Title similarity threshold: 95%" in output_text


def test_fixer_adds_only_confident_candidate(tmp_path, monkeypatch):
    source = tmp_path / "input.bib"
    output = tmp_path / "output.bib"
    source.write_text(
        """@article{sample,
  title = {A Simple Study},
  author = {Doe, Jane}
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["bibtex-doi-fixer", str(source), str(output)])
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
    assert "doi = {10.1000/found}" in output.read_text(encoding="utf-8")


def test_fixer_reports_entries_skipped_for_existing_doi(tmp_path, monkeypatch, capsys):
    source = tmp_path / "input.bib"
    output = tmp_path / "output.bib"
    source.write_text(
        """@article{existing,
  title = {Already Identified},
  doi = {10.1000/existing}
}
@article{missing,
  title = {A Simple Study},
  author = {Doe, Jane}
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["bibtex-doi-fixer", str(source), str(output)])
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
    output = capsys.readouterr().out
    assert "Added 1 DOI(s); skipped 1 entry(s) with an existing DOI; 0 entry(s) unchanged." in output
    assert "Progress [" in output
    assert "added: 1 | existing DOI: 1 | unchanged: 0" in output


def test_fixer_prompts_for_crossref_or_arxiv_candidate(tmp_path, monkeypatch, capsys):
    source = tmp_path / "input.bib"
    output = tmp_path / "output.bib"
    source.write_text(
        """@article{sample,
  title = {A Simple Study},
  author = {Doe, Jane}
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["bibtex-doi-fixer", str(source), str(output)])
    monkeypatch.setattr(
        cli,
        "search_works",
        lambda title, author, timeout: [
            {
                "DOI": "10.1000/crossref",
                "title": ["A Simple Study"],
                "author": [{"family": "Doe"}],
            }
        ],
    )
    monkeypatch.setattr(
        cli,
        "search_arxiv_works",
        lambda title, timeout: [
            {
                "DOI": "10.48550/arXiv.1234.56789",
                "title": ["A Simple Study"],
                "author": [{"family": "Doe"}],
            }
        ],
    )
    monkeypatch.setattr("builtins.input", lambda prompt: "a")

    assert cli.fix_main() == 0
    assert "doi = {10.48550/arXiv.1234.56789}" in output.read_text(encoding="utf-8")
    assert "MULTIPLE SOURCES: sample" in capsys.readouterr().out

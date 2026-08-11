from bibtex_doi_checker.bibtex import normalize_doi


def test_normalize_doi_accepts_identifiers_and_resolver_urls():
    assert normalize_doi("10.1000/example") == "10.1000/example"
    assert normalize_doi("https://doi.org/10.1000/example") == "10.1000/example"
    assert normalize_doi("http://dx.doi.org/10.1000/example.") == "10.1000/example"
    assert normalize_doi("⟨10.1145/3811280⟩") == "10.1145/3811280"
    assert normalize_doi("10.1109/VLSM.\n2001.938899") == "10.1109/VLSM.2001.938899"


def test_normalize_doi_rejects_invalid_values():
    assert normalize_doi("https://example.com/10.1000/example") is None
    assert normalize_doi("not a doi") is None

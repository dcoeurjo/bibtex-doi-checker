from bibtex_doi_checker.matching import compare_entry, select_candidate


ENTRY = {
    "ID": "sample",
    "title": "A {Simple} Study of DOI Matching",
    "author": "Doe, Jane and Smith, John",
}

WORK = {
    "DOI": "10.1000/sample",
    "title": ["A Simple Study of DOI Matching"],
    "author": [{"family": "Doe"}, {"family": "Smith"}],
}


def test_compare_entry_ignores_bibliography_formatting():
    comparison = compare_entry(ENTRY, WORK)
    assert comparison.matches
    assert comparison.title == 100
    assert comparison.author_overlap == 2


def test_select_candidate_requires_clear_high_confidence_match():
    selected = select_candidate(ENTRY, [WORK])
    assert selected == WORK

    ambiguous = {**WORK, "DOI": "10.1000/another"}
    assert select_candidate(ENTRY, [WORK, ambiguous]) is None


def test_select_candidate_uses_configured_title_threshold():
    near_match = {**WORK, "title": ["A Simple Study of DOI Match"]}

    assert select_candidate(ENTRY, [near_match], threshold=99) is None
    assert select_candidate(ENTRY, [near_match], threshold=90) == near_match


def test_select_candidate_uses_bibtex_year_to_break_an_exact_match_tie():
    entry = {**ENTRY, "year": "1999"}
    correct = {**WORK, "issued": {"date-parts": [[1999]]}}
    different_year = {
        **WORK,
        "DOI": "10.1000/different-year",
        "issued": {"date-parts": [[2017]]},
    }

    assert select_candidate(entry, [different_year, correct]) == correct

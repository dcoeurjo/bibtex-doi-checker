from io import BytesIO

from bibtex_doi_checker import arxiv
from bibtex_doi_checker.arxiv import arxiv_id_from_doi


def test_arxiv_id_from_doi_is_case_insensitive():
    assert arxiv_id_from_doi("10.48550/arXiv.1706.03762") == "1706.03762"
    assert arxiv_id_from_doi("10.1000/example") is None


def test_get_work_converts_arxiv_atom_metadata(monkeypatch):
    response = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title> Attention Is All You Need\n</title>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
  </entry>
</feed>"""

    class FakeResponse(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(arxiv, "urlopen", lambda request, timeout: FakeResponse(response))

    work = arxiv.get_work("10.48550/arXiv.1706.03762", 10)

    assert work == {
        "title": ["Attention Is All You Need"],
        "author": [{"family": "Vaswani"}, {"family": "Shazeer"}],
    }


def test_search_works_creates_doi_candidate(monkeypatch):
    response = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v1</id>
    <title>Attention Is All You Need</title>
    <author><name>Ashish Vaswani</name></author>
  </entry>
</feed>"""

    class FakeResponse(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(arxiv, "urlopen", lambda request, timeout: FakeResponse(response))

    assert arxiv.search_works("Attention Is All You Need", 10) == [
        {
            "DOI": "10.48550/arXiv.1706.03762",
            "title": ["Attention Is All You Need"],
            "author": [{"family": "Vaswani"}],
        }
    ]

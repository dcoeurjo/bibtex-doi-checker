"""Small arXiv API client for arXiv DOI metadata."""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ARXIV_API_URL = "https://export.arxiv.org/api/query"
USER_AGENT = "bibtex-doi-checker/0.1 (https://github.com/dcoeurjo/bibtex-doi-checker)"
ATOM = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivError(RuntimeError):
    """An arXiv request failed."""


def arxiv_id_from_doi(doi: str) -> str | None:
    """Return the arXiv identifier embedded in an arXiv DOI."""
    prefix = "10.48550/arxiv."
    return doi[len(prefix) :] if doi.casefold().startswith(prefix) else None


def get_work(doi: str, timeout: float) -> dict[str, Any]:
    """Fetch arXiv metadata for an arXiv DOI."""
    arxiv_id = arxiv_id_from_doi(doi)
    if not arxiv_id:
        raise ArxivError("not an arXiv DOI")
    entries = _query({"id_list": arxiv_id}, timeout)
    if not entries:
        raise ArxivError("paper not found")
    return _work(entries[0])


def search_works(title: str, timeout: float) -> list[dict[str, Any]]:
    """Search arXiv by title and return DOI-ready metadata candidates."""
    entries = _query({"search_query": f'ti:"{title}"', "max_results": 5}, timeout)
    candidates = []
    for entry in entries:
        identifier = entry.findtext("atom:id", default="", namespaces=ATOM).rstrip("/")
        arxiv_id = re.sub(r"v\d+$", "", identifier.rsplit("/", 1)[-1])
        if arxiv_id:
            candidates.append({**_work(entry), "DOI": f"10.48550/arXiv.{arxiv_id}"})
    return candidates


def _query(parameters: dict[str, Any], timeout: float) -> list[ElementTree.Element]:
    url = f"{ARXIV_API_URL}?{urlencode(parameters)}"
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/atom+xml"})
    try:
        with urlopen(request, timeout=timeout) as response:
            root = ElementTree.parse(response).getroot()
    except HTTPError as error:
        raise ArxivError(f"HTTP {error.code}") from error
    except URLError as error:
        raise ArxivError(str(error.reason)) from error
    except TimeoutError as error:
        raise ArxivError("request timed out") from error
    except ElementTree.ParseError as error:
        raise ArxivError("invalid XML response") from error
    return root.findall("atom:entry", ATOM)


def _work(entry: ElementTree.Element) -> dict[str, Any]:
    title = entry.findtext("atom:title", default="", namespaces=ATOM)
    authors = [
        {"family": name.split()[-1]}
        for author in entry.findall("atom:author", ATOM)
        if (name := author.findtext("atom:name", default="", namespaces=ATOM).strip())
    ]
    return {"title": [" ".join(title.split())], "author": authors}

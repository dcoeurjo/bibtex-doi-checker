"""Small Crossref REST API client."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.crossref.org/works"
USER_AGENT = "bibtex-doi-checker/0.1 (https://github.com/dcoeurjo/bibtex-doi-checker)"


class CrossrefError(RuntimeError):
    """A Crossref request failed."""


def _request(url: str, timeout: float) -> Any:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as error:
        raise CrossrefError(f"HTTP {error.code}") from error
    except URLError as error:
        raise CrossrefError(str(error.reason)) from error
    except TimeoutError as error:
        raise CrossrefError("request timed out") from error
    except json.JSONDecodeError as error:
        raise CrossrefError("invalid JSON response") from error
    return payload["message"]


def get_work(doi: str, timeout: float) -> dict[str, Any]:
    """Fetch Crossref metadata for a DOI."""
    return _request(f"{BASE_URL}/{quote(doi, safe='')}", timeout)


def search_works(title: str, author: str, timeout: float) -> list[dict[str, Any]]:
    """Search Crossref for candidate works."""
    query = urlencode({"query.bibliographic": f"{title} {author}", "rows": 5})
    message = _request(f"{BASE_URL}?{query}", timeout)
    return message.get("items", [])

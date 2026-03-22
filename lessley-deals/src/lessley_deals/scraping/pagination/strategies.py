from __future__ import annotations

from typing import Any, Protocol


class PaginationStrategy(Protocol):
    """Protocol for page-iteration strategies."""

    def first_page_params(self) -> dict[str, Any]:
        """Return query-params for the first page request."""
        ...

    def next_page_params(
        self,
        response_data: Any,
        current_params: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Return params for the next page, or *None* when pagination is exhausted."""
        ...


class SinglePage:
    """No pagination – the source returns everything in one request."""

    def first_page_params(self) -> dict[str, Any]:
        return {}

    def next_page_params(
        self,
        response_data: Any,
        current_params: dict[str, Any],
    ) -> dict[str, Any] | None:
        return None


class PageNumber:
    """Classic ``?page=N`` pagination.

    Parameters
    ----------
    page_param:
        Name of the page query parameter.
    start_page:
        Page number of the first page (typically ``1``).
    results_key:
        Key in the JSON response that holds the results list.  An empty list
        signals the last page.
    """

    def __init__(
        self,
        page_param: str = "page",
        start_page: int = 1,
        results_key: str = "results",
    ) -> None:
        self._page_param = page_param
        self._start_page = start_page
        self._results_key = results_key

    def first_page_params(self) -> dict[str, Any]:
        return {self._page_param: self._start_page}

    def next_page_params(
        self,
        response_data: Any,
        current_params: dict[str, Any],
    ) -> dict[str, Any] | None:
        # Detect last page: empty or missing results list
        results = (
            response_data.get(self._results_key, [])
            if isinstance(response_data, dict)
            else response_data
        )
        if not results:
            return None

        current_page: int = current_params.get(self._page_param, self._start_page)
        return {**current_params, self._page_param: current_page + 1}


class OffsetLimit:
    """Offset/limit pagination (``?offset=N&limit=M``).

    Parameters
    ----------
    limit:
        Number of items per page.
    offset_param:
        Name of the offset query parameter.
    limit_param:
        Name of the limit query parameter.
    results_key:
        Key in the JSON response that holds the results list.  Fewer results
        than *limit* signals the last page.
    """

    def __init__(
        self,
        limit: int = 50,
        offset_param: str = "offset",
        limit_param: str = "limit",
        results_key: str = "results",
    ) -> None:
        self._limit = limit
        self._offset_param = offset_param
        self._limit_param = limit_param
        self._results_key = results_key

    def first_page_params(self) -> dict[str, Any]:
        return {self._offset_param: 0, self._limit_param: self._limit}

    def next_page_params(
        self,
        response_data: Any,
        current_params: dict[str, Any],
    ) -> dict[str, Any] | None:
        results = (
            response_data.get(self._results_key, [])
            if isinstance(response_data, dict)
            else response_data
        )
        if len(results) < self._limit:
            return None

        current_offset: int = current_params.get(self._offset_param, 0)
        return {
            **current_params,
            self._offset_param: current_offset + self._limit,
            self._limit_param: self._limit,
        }

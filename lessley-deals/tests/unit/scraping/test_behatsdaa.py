from __future__ import annotations

import pytest
from datetime import datetime, timezone
from typing import Any

from lessley_deals.scraping.sources.behatsdaa import BehatsdaaAdapter
from lessley_deals.scraping.base import SourceConfig


class TestBehatsdaaAdapter:
    def test_source_id(self) -> None:
        adapter = BehatsdaaAdapter(
            SourceConfig(base_url="https://back.behatsdaa.org.il")
        )
        assert adapter.source_id == "behatsdaa"

    def test_auth_headers_include_org_id(self) -> None:
        adapter = BehatsdaaAdapter(
            SourceConfig(base_url="https://back.behatsdaa.org.il"),
            organization_id="42",
        )
        headers = adapter._auth_headers()
        assert headers["organizationid"] == "42"
        assert headers["native"] == "true"

    def test_auth_headers_include_access_token(self) -> None:
        adapter = BehatsdaaAdapter(
            SourceConfig(base_url="https://back.behatsdaa.org.il"),
            access_token="my-secret-token",
        )
        headers = adapter._auth_headers()
        assert headers["AccessToken"] == "my-secret-token"

    def test_auth_headers_no_token_when_empty(self) -> None:
        adapter = BehatsdaaAdapter(
            SourceConfig(base_url="https://back.behatsdaa.org.il"),
        )
        headers = adapter._auth_headers()
        assert "AccessToken" not in headers

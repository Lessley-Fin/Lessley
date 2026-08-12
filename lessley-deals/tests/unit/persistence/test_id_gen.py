from __future__ import annotations

import re
import time

from lessley_deals.persistence.id_gen import generate_id


class TestGenerateId:
    def test_uniqueness(self) -> None:
        """Generate 1000 IDs and assert no duplicates."""
        ids = [generate_id() for _ in range(1000)]
        assert len(set(ids)) == 1000

    def test_sortable(self) -> None:
        """IDs generated in sequence should be lexicographically ordered."""
        ids: list[str] = []
        for _ in range(50):
            ids.append(generate_id())
        # The timestamp prefix ensures chronological ordering
        # (within the same millisecond, random suffix may not sort,
        # but across different milliseconds they will)
        # We just verify non-decreasing by timestamp prefix
        prefixes = [id_.split("_")[0] for id_ in ids]
        assert prefixes == sorted(prefixes)

    def test_format(self) -> None:
        """ID format: 12-char hex timestamp + underscore + 16-char hex random."""
        id_ = generate_id()
        pattern = r"^[0-9a-f]{12}_[0-9a-f]{16}$"
        assert re.match(pattern, id_), f"ID {id_!r} does not match expected format"

    def test_contains_underscore_separator(self) -> None:
        id_ = generate_id()
        assert "_" in id_
        parts = id_.split("_")
        assert len(parts) == 2

    def test_timestamp_prefix_is_recent(self) -> None:
        """The hex timestamp should decode to approximately current time in ms."""
        id_ = generate_id()
        ts_hex = id_.split("_")[0]
        ts_ms = int(ts_hex, 16)
        now_ms = int(time.time() * 1000)
        # Should be within 5 seconds
        assert abs(ts_ms - now_ms) < 5000

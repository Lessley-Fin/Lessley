"""Cross-process run locks.

Within one process the scheduler already guarantees a source never overlaps
itself (one loop per source).  Across *replicas* it cannot — and two containers
scraping HOT simultaneously means double the traffic, double the ban risk and a
race on the head rows.

``MongoLeaseLock`` is a lease: a document per source with an expiry.  Acquiring
is a single atomic ``find_one_and_update``, so exactly one replica wins.  If a
holder crashes, the lease simply expires and the next run recovers — no manual
cleanup, no stuck source.
"""

from __future__ import annotations

import logging
import os
import socket
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from lessley_deals.persistence.id_gen import generate_id

logger = logging.getLogger(__name__)


def _owner_id() -> str:
    """Identify this process in lock documents (useful when debugging)."""
    return f"{socket.gethostname()}:{os.getpid()}"


class RunLock(Protocol):
    def acquire(self, key: str, ttl_seconds: float) -> str | None:
        """Return a lease token, or None if somebody else holds the lock."""
        ...

    def renew(self, key: str, token: str, ttl_seconds: float) -> bool: ...
    def release(self, key: str, token: str) -> None: ...


class NullRunLock:
    """Single-replica / local development: always acquires."""

    def acquire(self, key: str, ttl_seconds: float) -> str | None:
        return generate_id()

    def renew(self, key: str, token: str, ttl_seconds: float) -> bool:
        return True

    def release(self, key: str, token: str) -> None:
        return None


class MongoLeaseLock:
    """Lease-based lock stored in the ``scheduler_locks`` collection."""

    def __init__(self, db: Any, collection_name: str = "scheduler_locks") -> None:
        self._col = db[collection_name]
        self._owner = _owner_id()
        # Belt and braces: the code always releases or lets the lease lapse, but
        # a TTL index also garbage-collects documents nobody will ever touch.
        self._col.create_index("expires_at", expireAfterSeconds=3600, name="ttl_expires_at")

    def acquire(self, key: str, ttl_seconds: float) -> str | None:
        now = datetime.now(timezone.utc)
        token = generate_id()
        lease = {
            "token": token,
            "owner": self._owner,
            "acquired_at": now,
            "expires_at": now + timedelta(seconds=ttl_seconds),
        }

        # Case 1 — no lock document yet.  The unique _id index makes exactly one
        # concurrent insert win; the losers fall through to case 2.
        try:
            self._col.insert_one({"_id": key, **lease})
            return token
        except Exception as exc:
            if "E11000" not in str(exc):
                logger.warning("Lock acquire failed for %s: %s", key, exc)
                return None

        # Case 2 — a document exists.  Take it over only if the lease lapsed.
        # MongoDB re-evaluates the filter atomically under the document lock, so
        # two replicas racing an expired lease cannot both succeed.
        result = self._col.update_one(
            {"_id": key, "expires_at": {"$lte": now}}, {"$set": lease}
        )
        return token if result.modified_count else None

    def renew(self, key: str, token: str, ttl_seconds: float) -> bool:
        """Extend a lease we still hold — call this from long-running scrapes."""
        now = datetime.now(timezone.utc)
        result = self._col.update_one(
            {"_id": key, "token": token},
            {"$set": {"expires_at": now + timedelta(seconds=ttl_seconds)}},
        )
        return bool(result.modified_count)

    def release(self, key: str, token: str) -> None:
        # Only the holder may release — a stale token must never free somebody
        # else's freshly-acquired lock.
        self._col.delete_one({"_id": key, "token": token})

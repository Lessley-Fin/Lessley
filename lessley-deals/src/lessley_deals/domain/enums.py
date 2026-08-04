from enum import StrEnum


class MatchDecision(StrEnum):
    AUTO_MATCH = "auto_match"
    REVIEW = "review"
    NO_MATCH = "no_match"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    CREATED = "created"
    DISCARDED = "discarded"
    SKIPPED = "skipped"


class ReviewAction(StrEnum):
    APPROVE = "approve"
    CREATE_NEW = "create_new"
    DISCARD = "discard"
    SKIP = "skip"


class AliasSource(StrEnum):
    SEED = "seed"
    SCRAPER = "scraper"
    REVIEW = "review"
    MANUAL = "manual"


class RecordFate(StrEnum):
    AUTO_MATCHED = "auto_matched"
    SENT_TO_REVIEW = "sent_to_review"
    NO_MATCH = "no_match"
    DUPLICATE = "duplicate"
    ERROR = "error"


class DealLifecycleStatus(StrEnum):
    """State a deal was in during a version's validity window.

    ACTIVE   – on offer.
    EXPIRED  – the source stopped offering it (or its own end date passed).

    Deliberately *not* a "superseded" value: whether a version is the latest is
    already expressed by ``is_current`` / ``valid_to``.  Folding that into the
    status would overwrite what the deal actually *was* during that window and
    make point-in-time queries lie.
    """

    ACTIVE = "active"
    EXPIRED = "expired"


class DealChangeType(StrEnum):
    """What the ingestion service decided about an incoming deal."""

    NEW = "new"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    EXPIRED = "expired"
    REACTIVATED = "reactivated"


class RunStatus(StrEnum):
    """Lifecycle of a single scheduled scrape run (see scheduling.journal)."""

    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"

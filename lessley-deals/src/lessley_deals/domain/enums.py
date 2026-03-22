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

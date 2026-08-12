"""Deal versioning: business identity, content hashing and SCD Type 2 ingestion.

The rule this package enforces: **raw data is never overwritten**.  Every change
to a deal produces a new immutable ``DealVersion`` row, while a ``CurrentDeal``
head row always points at the latest state.  Consumers read the heads; auditors,
"what changed" reports and price-history charts read the versions.
"""

from lessley_deals.versioning.hashing import (
    DealIdentityResolver,
    compute_content_hash,
    diff_snapshots,
    extract_source_expiry,
)
from lessley_deals.versioning.ingestion import (
    IngestionConfig,
    IngestionPlan,
    IngestionReport,
    IngestionService,
    plan_ingestion,
)

__all__ = [
    "DealIdentityResolver",
    "IngestionConfig",
    "IngestionPlan",
    "IngestionReport",
    "IngestionService",
    "compute_content_hash",
    "diff_snapshots",
    "extract_source_expiry",
    "plan_ingestion",
]

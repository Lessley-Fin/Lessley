from __future__ import annotations

import logging
from datetime import datetime, timezone

from lessley_deals.domain.enums import AliasSource
from lessley_deals.domain.models import StoreAlias
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.review.actions import build_name_forms

logger = logging.getLogger(__name__)


class AliasLearner:
    """Learns new store aliases from review decisions."""

    def __init__(self, alias_repo: AliasJsonRepository) -> None:
        self._repo = alias_repo

    def learn_from_approval(self, input_name: str, store_id: str) -> StoreAlias:
        """Create an alias from an approved review linking input_name to an existing store."""
        logger.info(
            "Learning alias from approval: '%s' -> store %s",
            input_name, store_id,
        )
        alias = StoreAlias(
            id=generate_id(),
            store_id=store_id,
            alias=input_name,
            alias_forms=build_name_forms(input_name),
            source=AliasSource.REVIEW,
            created_at=datetime.now(timezone.utc),
        )
        self._repo.save(alias)
        return alias

    def learn_from_creation(self, input_name: str, store_id: str) -> StoreAlias:
        """Create an alias from a newly created store linking input_name to it."""
        logger.info(
            "Learning alias from creation: '%s' -> store %s",
            input_name, store_id,
        )
        alias = StoreAlias(
            id=generate_id(),
            store_id=store_id,
            alias=input_name,
            alias_forms=build_name_forms(input_name),
            source=AliasSource.REVIEW,
            created_at=datetime.now(timezone.utc),
        )
        self._repo.save(alias)
        return alias

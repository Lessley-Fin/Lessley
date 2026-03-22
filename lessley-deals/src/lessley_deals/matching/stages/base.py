from __future__ import annotations

from abc import ABC, abstractmethod

from lessley_deals.domain.models import MatchCandidate, NormalizedRecord
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex


class MatchStage(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def evaluate(
        self,
        normalized: NormalizedRecord,
        index: AliasIndex,
        config: MatchConfig,
    ) -> MatchCandidate | None:
        """Return best candidate from this stage, or None."""
        ...

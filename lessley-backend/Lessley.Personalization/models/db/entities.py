"""The scraping pipeline's own documents, read directly.

These bind ``clubs``/``stores``/``deals`` — the collections ``lessley-deals`` writes and
``deal-optimizer`` reads — rather than the ``*_list`` projection that used to sit in
between. Two consequences of that move show up in every model here:

* timestamps arrive as ISO strings, which pydantic parses into ``datetime`` on its own;
* **the business key lives in one of two places**, so it is read from either.

The pipeline's repositories pop ``id`` into ``_id``, so a scraped row's ``_id`` *is* the
business key. Rows loaded with ``mongoimport`` from ``main/resources/*.json`` instead keep
their ``id`` field and get a generated ObjectId ``_id``. Both are in live databases, and a
model that assumes one crashes on the other — Beanie validates every document as it loads
and one bad row aborts the whole read, which takes this service down at startup rather than
degrading it. ``deal-optimizer``'s ``deals_source`` reads both shapes for the same reason.

Use the ``club_id``/``deal_id``/``store_id`` properties rather than ``.id``: they resolve to
the business key whichever shape the row is in, and are the names callers already used.
"""

from datetime import datetime
from typing import Any, Dict, List

from beanie import Document
from pydantic import BaseModel, Field, field_validator


def _business_key(business_id: str | None, mongo_id: Any) -> str:
    """The business key: the ``id`` field when present, else the ``_id`` it was written as."""
    if business_id:
        return business_id
    return "" if mongo_id is None else str(mongo_id)


class Club(Document):
    # Any, not str: an imported row's _id is an ObjectId. See the module docstring.
    id: Any = Field(default=None, alias="_id")
    business_id: str | None = Field(default=None, alias="id")
    name: str
    source_id: str
    description: str | None = None
    metadata: Dict[str, Any] = {}
    stores: List[str] = []

    @property
    def club_id(self) -> str:
        """The business key, under the name callers already use."""
        return _business_key(self.business_id, self.id)

    class Settings:
        name = "clubs"


class Deal(Document):
    id: Any = Field(default=None, alias="_id")
    business_id: str | None = Field(default=None, alias="id")
    store_id: str
    # Optional for the same reason as club_id below: one row missing it must not abort the
    # entire load. Imported dumps do carry it.
    raw_id: str | None = None
    source_id: str | None = None
    scraped_at: datetime
    resolved_at: datetime | None = None
    title: str | None = None
    deal_description: str | None = None
    # Filled by the pipeline's PersistStage from source_id. Optional because rows written
    # before that map existed hold null, and Beanie fails the *entire* load on one invalid
    # document — a missing club must cost that deal its club badge, not take recommendations
    # down for everyone. ``python -m deals backfill-club-ids`` repairs those rows.
    club_id: str | None = None

    @property
    def deal_id(self) -> str:
        return _business_key(self.business_id, self.id)

    class Settings:
        name = "deals"


class MccCode(Document):
    """Unchanged: ``mccs`` is already shared — ``lessley-deals`` seeds it from
    ``data/seed/mccs.json``, so there is no second copy to unify."""

    mcc: str
    category: str

    class Settings:
        name = "mccs"


class NameForms(BaseModel):
    normalized: str
    compact: str
    tokens: List[str]


class StoreMetadata(BaseModel):
    image_urls: List[str] = Field(default_factory=list)
    mcc_codes: List[str] = Field(default_factory=list)
    store_url: str | None = None
    # The shop's English name where the display name is Hebrew ('עיל"מ' / 'Herbology').
    # Matched against as an alternative spelling, so a feed reporting either one lands.
    official_name: str | None = None

    @field_validator("mcc_codes", mode="before")
    @classmethod
    def _codes_as_text(cls, value: Any) -> Any:
        """Category names ("GROCERIES") today, but pre-catalogue rows still hold the raw
        4-digit MCC as a number. The old projection stringified them on the way out; doing
        it here keeps one legacy row from failing the whole store load."""
        if isinstance(value, list):
            return [str(code) for code in value if code is not None]
        return value


class Store(Document):
    id: Any = Field(default=None, alias="_id")
    business_id: str | None = Field(default=None, alias="id")
    name: str
    # Optional for the same reason as Deal.club_id: Beanie validates every document as it
    # loads and one bad row aborts the whole read. The projection that used to sit in front
    # of this collection silently dropped stores with no usable timestamps or name forms —
    # omitting a store from recommendations beats taking recommendations down for all of
    # them. Nothing reads these three, so a null costs nothing.
    name_forms: NameForms | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: StoreMetadata = Field(default_factory=StoreMetadata)

    @property
    def store_id(self) -> str:
        return _business_key(self.business_id, self.id)

    class Settings:
        name = "stores"

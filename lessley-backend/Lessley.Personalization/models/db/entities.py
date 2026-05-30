from datetime import datetime
from typing import Any, Dict, List

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class Club(Document):
    id: PydanticObjectId = Field(default_factory=PydanticObjectId, alias="_id")
    club_id: str = Field(..., alias="id")
    name: str
    source_id: str
    description: str | None = None
    metadata: Dict[str, Any] = {}
    stores: List[str] = []

    class Settings:
        name = "club_list"


class Deal(Document):
    id: PydanticObjectId = Field(default_factory=PydanticObjectId, alias="_id")
    deal_id: str = Field(..., alias="id")
    store_id: str
    raw_id: str
    source_id: str
    scraped_at: datetime
    resolved_at: datetime | None = None
    title: str
    deal_description: str | None = None
    club_id: str

    class Settings:
        name = "deal_list"


class MccCode(Document):
    id: PydanticObjectId = Field(default_factory=PydanticObjectId, alias="_id")
    mcc: str
    edited_description: str | None = None
    combined_description: str | None = None
    usda_description: str | None = None
    irs_description: str | None = None
    irs_reportable: str | None = None

    class Settings:
        name = "mcc_list"


class NameForms(BaseModel):
    normalized: str
    compact: str
    tokens: List[str]


class StoreMetadata(BaseModel):
    image_urls: List[str] = Field(default_factory=list)
    mcc_codes: List[int] = Field(default_factory=list)
    store_url: str | None = None


class Store(Document):
    id: PydanticObjectId = Field(default_factory=PydanticObjectId, alias="_id")
    store_id: str = Field(..., alias="id")
    name: str
    name_forms: NameForms
    created_at: datetime
    updated_at: datetime
    metadata: StoreMetadata

    class Settings:
        name = "store_list"

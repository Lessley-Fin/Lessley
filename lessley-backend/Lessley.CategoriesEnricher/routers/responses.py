from pydantic import BaseModel, Field
from typing import Generic, TypeVar
from datetime import datetime

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Consistent response format for all endpoints"""

    status: str  # "success" or "error"
    count: int | None = None
    data: T | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BasicResponse(BaseModel):
    """Basic response format for endpoints that don't return data"""

    status: str  # "success" or "error"
    data: T | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

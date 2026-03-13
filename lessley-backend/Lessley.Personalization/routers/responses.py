from pydantic import BaseModel, Field
from typing import Generic, TypeVar
from datetime import datetime

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Consistent response format for all endpoints"""

    status: str  # "success" or "error"
    data: T | None = None
    message: str | None = None
    count: int | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

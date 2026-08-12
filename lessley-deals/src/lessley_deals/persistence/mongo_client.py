"""MongoDB client factory — reads connection config from environment."""

from __future__ import annotations

import os

from pymongo import MongoClient
from pymongo.database import Database


def get_database() -> Database:  # type: ignore[type-arg]
    """Return a pymongo Database using MONGO_URI / MONGO_DB env vars."""
    uri = os.environ.get("MONGO_URI", "mongodb://guest:guest@localhost:27017/lessley?authSource=admin")
    db_name = os.environ.get("MONGO_DB", "lessley")
    client: MongoClient = MongoClient(uri, serverSelectionTimeoutMS=5000)  # type: ignore[type-arg]
    return client[db_name]

from __future__ import annotations

import pytest
from pathlib import Path

from lessley_deals.persistence.config import PersistenceConfig


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def persistence_config(data_dir: Path) -> PersistenceConfig:
    config = PersistenceConfig(base_dir=data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return config

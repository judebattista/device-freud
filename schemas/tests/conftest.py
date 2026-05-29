"""Pytest fixtures shared across schema tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

SCHEMAS_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SCHEMAS_ROOT / "device-interface.schema.json"
EXAMPLES_DIR = SCHEMAS_ROOT / "examples"
INVALID_DIR = EXAMPLES_DIR / "invalid"


@pytest.fixture(scope="session")
def schema() -> dict:
    with SCHEMA_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="session")
def schema_path() -> Path:
    return SCHEMA_PATH


@pytest.fixture(scope="session")
def examples_dir() -> Path:
    return EXAMPLES_DIR


@pytest.fixture(scope="session")
def invalid_dir() -> Path:
    return INVALID_DIR

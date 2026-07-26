# tests/conftest.py — shared pytest fixtures
import asyncio
import sys

import pytest


@pytest.fixture(scope="session")
def event_loop_policy():
    """asyncpg on Windows needs SelectorEventLoop, not the default Proactor."""
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: loads a real model; excluded from the default run"
    )

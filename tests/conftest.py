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


@pytest.fixture(autouse=True)
def _isolate_turn_memory():
    """Clear per-user turn memory between tests.

    last_attack and pending_clarify hold module-level dicts keyed by user id, so
    without this a test that leaves state for "player1" changes how a later test's
    tool loop routes.
    """
    from src import last_attack, pending_clarify

    last_attack._LAST.clear()
    pending_clarify._PENDING.clear()
    yield
    last_attack._LAST.clear()
    pending_clarify._PENDING.clear()


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: loads a real model; excluded from the default run"
    )

"""Shared pytest fixtures for the Sensofy integration tests."""

import sys
from pathlib import Path

import pytest

# Make `custom_components.sensofy` importable when running from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True, scope="session")
def _warm_async_resolver():
    """Spawn the pycares DNS resolver thread once before any test.

    aiohttp's AsyncResolver lazily starts a daemon thread (pycares
    `_run_safe_shutdown_loop`) the first time a client session is created. The
    test harness's per-test "no new threads" check would otherwise attribute
    that one-off daemon thread to whichever test first makes an HTTP call. By
    starting it at session scope it lands in every test's baseline snapshot.
    """
    channel = None
    try:
        import pycares

        channel = pycares.Channel()
    except Exception:  # pragma: no cover - best effort warm-up
        channel = None
    yield channel


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of the custom integration in every test."""
    yield

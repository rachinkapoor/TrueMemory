"""Shared pytest fixtures — test isolation for the whole suite.

Issue #426 (flaky CI): several tests mutate process-global state that leaks
into later tests *and* into the subprocesses spawned by the CLI tests
(``tests/test_cli_help.py`` runs ``truememory-*`` via ``subprocess`` and
inherits ``os.environ``). The classic symptom is
``test_cli_help::test_ingest_version_flag_exits_cleanly`` passing in isolation
but failing in full-suite order, and ``tests/test_upgrade_path.py`` depending
on the ambient ``~/.truememory/config.json`` tier (which decides
``vector_search.EMBEDDING_MODEL`` at import time).

Two autouse fixtures restore determinism without weakening any assertion:

1. ``_isolate_environ`` snapshots ``os.environ`` before each test and restores
   it after, so direct ``os.environ[...] = ...`` writes (which are NOT
   monkeypatch and therefore not auto-reverted) cannot leak across tests or
   into spawned subprocesses.
2. ``_isolate_vector_search_globals`` snapshots the module-level embedder
   globals (``EMBEDDING_MODEL``, ``_embedding_dim``, ``_model``) and restores
   them after each test, so a test that switches tiers does not poison the
   next one.
"""
from __future__ import annotations

import os
import sqlite3

import pytest


def _can_load_sqlite_vec() -> bool:
    """True if sqlite-vec can be loaded into a connection."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.enable_load_extension(True)
        import sqlite_vec
        sqlite_vec.load(conn)
        return True
    except (AttributeError, ImportError, OSError):
        return False
    finally:
        conn.close()


can_load_extensions = _can_load_sqlite_vec()

requires_sqlite_ext = pytest.mark.skipif(
    not can_load_extensions,
    reason="sqlite-vec not available (missing enable_load_extension or sqlite_vec package)",
)


@pytest.fixture(autouse=True)
def _isolate_environ():
    """Snapshot/restore ``os.environ`` around every test.

    Plain ``os.environ[...] = ...`` writes in some env-driven tests are not
    monkeypatch-managed, so without this they persist for the rest of the
    session and are inherited by subprocess-based CLI tests.
    """
    snapshot = dict(os.environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(snapshot)


@pytest.fixture(autouse=True)
def _isolate_vector_search_globals():
    """Snapshot/restore ``truememory.vector_search`` embedder globals.

    These are process-global (module-level) and several tests mutate them via
    ``set_embedding_model`` or ``monkeypatch.setattr``. monkeypatch reverts the
    ones it owns, but a defensive snapshot here keeps the embedder identity
    deterministic regardless of test order or ambient config.json.
    """
    try:
        from truememory import vector_search as _vs
    except Exception:
        # vector_search may be unimportable in minimal-dep environments; nothing
        # to isolate in that case.
        yield
        return

    saved = (
        getattr(_vs, "EMBEDDING_MODEL", None),
        getattr(_vs, "_embedding_dim", None),
        getattr(_vs, "_model", None),
    )
    try:
        yield
    finally:
        _vs.EMBEDDING_MODEL, _vs._embedding_dim, _vs._model = saved


@pytest.fixture(autouse=True)
def _isolate_model_client_timeout():
    """Snapshot/restore ``truememory.model_client._default_request_timeout``.

    Hook recall paths arm a process-wide model-server deadline via
    ``set_request_timeout`` (issue #577). In production the hooks are
    short-lived standalone processes, but in the test suite any test that
    exercises a recall path would otherwise leak the 5s deadline into later
    tests that assert the legacy 120s autostart-retry behavior.
    """
    try:
        from truememory import model_client
    except Exception:
        yield
        return

    saved = model_client._default_request_timeout
    try:
        yield
    finally:
        model_client._default_request_timeout = saved

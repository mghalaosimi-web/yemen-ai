"""
app/services/intelligence_provider.py
======================================
Canonical singleton for the IntelligenceService.

ALL application code that needs the intelligence engine must import from
here.  This guarantees exactly one in-memory vector store, one knowledge
graph, one memory service and one AI provider per process.

Usage:
    from app.services.intelligence_provider import get_intelligence

    service = get_intelligence()

The instance is created lazily on the first call and reused forever.
Tests that need an isolated instance should call reset_intelligence() in
their teardown to avoid cross-test pollution.
"""
from __future__ import annotations
import threading
from typing import Optional

_lock = threading.Lock()
_instance: Optional["IntelligenceService"] = None  # type: ignore[name-defined]


def get_intelligence():
    """Return the process-wide IntelligenceService singleton."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                from backend.services.intelligence_service import IntelligenceService
                _instance = IntelligenceService()
    return _instance


def set_intelligence(service) -> None:
    """Override the singleton — intended for startup wiring and tests only."""
    global _instance
    with _lock:
        _instance = service


def reset_intelligence() -> None:
    """Clear the singleton — use in test teardown for isolation."""
    global _instance
    with _lock:
        _instance = None

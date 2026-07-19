from __future__ import annotations

from functools import lru_cache

from src.core.config import get_settings
from src.core.events import EventBus
from src.infrastructure.event_bus import InMemoryEventBus


@lru_cache
def get_event_bus() -> EventBus:
    return InMemoryEventBus()


__all__ = ["get_settings", "get_event_bus"]

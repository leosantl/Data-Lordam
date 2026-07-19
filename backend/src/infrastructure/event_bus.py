from __future__ import annotations

import logging
from collections import defaultdict

from src.core.events import DomainEvent, EventHandler

logger = logging.getLogger(__name__)


class InMemoryEventBus:
    """Process-local event bus. Used in Phase 0 / tests; swap for a Redis
    Streams-backed implementation once multiple workers need to share events."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._handlers[event_name].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(event.event_name, [])
        if not handlers:
            logger.debug("no handlers registered for event %s", event.event_name)
        for handler in handlers:
            await handler(event)

"""轻量事件总线: monitor/stream 事件 → WebSocket 广播。"""
import asyncio
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("bedcode")


@dataclass
class Event:
    type: str  # status, screenshot, text, prompt, result, completion
    data: dict = field(default_factory=dict)


class EventBus:
    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=200)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._subscribers = [s for s in self._subscribers if s is not q]

    async def emit(self, event: Event):
        dead = []
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._subscribers.remove(q)


bus = EventBus()

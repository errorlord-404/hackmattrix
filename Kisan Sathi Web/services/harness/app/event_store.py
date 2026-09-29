from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path
from threading import Lock
from typing import Any, Callable, cast

from .protocol import EventEnvelope, EventKind, ResumeSnapshot


class ResumeWindowExpired(LookupError):
    def __init__(self, snapshot: ResumeSnapshot) -> None:
        super().__init__("resume_window_expired")
        self.snapshot = snapshot
        self.code = "resume_window_expired"


class EventStore:
    """Append-before-publish in-memory event log with bounded retention.

    Production can replace the storage engine without changing the envelope or
    replay contract; tests deliberately exercise the same ordering semantics.
    """

    def __init__(self, *, max_age_seconds: int = 86_400, max_events: int = 10_000, max_bytes: int = 10 * 1024 * 1024, storage_path: Path | None = None) -> None:
        self.max_age_seconds = max(1, max_age_seconds)
        self.max_events = max(1, max_events)
        self.max_bytes = max(1024, max_bytes)
        self._events: dict[str, list[tuple[float, EventEnvelope]]] = defaultdict(list)
        self._next: dict[str, int] = defaultdict(int)
        self._snapshots: dict[str, ResumeSnapshot] = {}
        self._listeners: dict[str, list[Callable[[EventEnvelope], None]]] = defaultdict(list)
        self._lock = Lock()
        self.storage_path = storage_path.expanduser().resolve() if storage_path else None
        self._load()

    def _load(self) -> None:
        if self.storage_path is None or not self.storage_path.is_file():
            return
        try:
            records = self.storage_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        for line in records:
            try:
                record = json.loads(line)
                event_data = record["event"]
                session_id = str(event_data["session_id"])
                event = EventEnvelope(
                    session_id=session_id,
                    turn_id=str(event_data["turn_id"]),
                    sequence=int(event_data["sequence"]),
                    kind=cast(EventKind, event_data["kind"]),
                    payload=dict(event_data.get("payload") or {}),
                    event_id=str(event_data.get("event_id") or ""),
                    occurred_at=str(event_data.get("occurred_at") or ""),
                )
                issued = float(record.get("issued_at", time.time()))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
            self._events[session_id].append((issued, event))
            self._next[session_id] = max(self._next[session_id], event.sequence)
            self._snapshots[session_id] = ResumeSnapshot(session_id, "active", event.sequence)
        for session_id in tuple(self._events):
            self._trim(session_id, time.time())

    def _persist(self, issued: float, event: EventEnvelope) -> None:
        if self.storage_path is None:
            return
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with self.storage_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"issued_at": issued, "event": event.as_dict()}, separators=(",", ":"), ensure_ascii=False) + "\n")
        except OSError:
            # Persistence failure must not turn an already-created event into a
            # phantom success; callers can inspect readiness/volume health.
            raise RuntimeError("event persistence is unavailable")

    def _trim(self, session_id: str, now: float) -> None:
        values = self._events[session_id]
        values[:] = [(issued, event) for issued, event in values if now - issued <= self.max_age_seconds]
        while len(values) > self.max_events or sum(len(event.ndjson().encode("utf-8")) for _, event in values) > self.max_bytes:
            values.pop(0)

    def append(self, session_id: str, turn_id: str, kind: EventKind, payload: dict[str, Any], *, snapshot_state: str = "active") -> EventEnvelope:
        now = time.time()
        with self._lock:
            self._trim(session_id, now)
            sequence = self._next[session_id] + 1
            event = EventEnvelope(session_id=session_id, turn_id=turn_id, sequence=sequence, kind=kind, payload=payload)
            self._next[session_id] = sequence
            self._events[session_id].append((now, event))
            self._trim(session_id, now)
            self._snapshots[session_id] = ResumeSnapshot(session_id, snapshot_state, sequence)
            self._persist(now, event)
            listeners = tuple(self._listeners.get(session_id, ()))
        # Publication is deliberately after the append lock is released.
        for listener in listeners:
            listener(event)
        return event

    def subscribe(self, session_id: str, listener: Callable[[EventEnvelope], None]) -> Callable[[], None]:
        with self._lock:
            self._listeners[session_id].append(listener)
        def unsubscribe() -> None:
            with self._lock:
                if listener in self._listeners.get(session_id, []):
                    self._listeners[session_id].remove(listener)
        return unsubscribe

    def replay(self, session_id: str, after: int = 0) -> list[EventEnvelope]:
        now = time.time()
        with self._lock:
            self._trim(session_id, now)
            values = [event for _, event in self._events.get(session_id, [])]
            snapshot = self._snapshots.get(session_id, ResumeSnapshot(session_id, "unknown", self._next.get(session_id, 0)))
            if values and after < values[0].sequence - 1:
                raise ResumeWindowExpired(snapshot)
            if not values and after < self._next.get(session_id, 0):
                raise ResumeWindowExpired(snapshot)
            return [EventEnvelope(session_id=event.session_id, turn_id=event.turn_id, sequence=event.sequence, kind=event.kind, payload=event.payload, event_id=event.event_id, occurred_at=event.occurred_at, replay=True, duplicate=False) for event in values if event.sequence > after]

    def snapshot(self, session_id: str) -> ResumeSnapshot:
        with self._lock:
            return self._snapshots.get(session_id, ResumeSnapshot(session_id, "unknown", self._next.get(session_id, 0)))

    def json_size(self, session_id: str) -> int:
        with self._lock:
            return sum(len(json.dumps(event.as_dict(), separators=(",", ":")).encode("utf-8")) for _, event in self._events.get(session_id, ()))

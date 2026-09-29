from __future__ import annotations

import pytest
from pathlib import Path

from app.event_store import EventStore, ResumeWindowExpired


def test_event_store_appends_before_publish_and_replays_in_sequence() -> None:
    store = EventStore(max_events=10)
    published = []
    store.subscribe("session-a", published.append)
    first = store.append("session-a", "turn-a", "ready", {"status": "ready"})
    second = store.append("session-a", "turn-a", "agentMessageDelta", {"text": "namaste"})
    assert [event.sequence for event in published] == [1, 2]
    replay = store.replay("session-a", after=1)
    assert [event.sequence for event in replay] == [2]
    assert replay[0].replay is True
    assert first.sequence == 1 and second.sequence == 2


def test_old_cursor_reports_snapshot_when_retention_window_expires() -> None:
    store = EventStore(max_events=2)
    store.append("session-a", "turn-a", "ready", {})
    store.append("session-a", "turn-a", "agentMessageDelta", {"text": "one"})
    store.append("session-a", "turn-a", "agentMessageCompleted", {"text": "one"})
    with pytest.raises(ResumeWindowExpired) as error:
        store.replay("session-a", after=0)
    assert error.value.code == "resume_window_expired"
    assert error.value.snapshot.last_sequence == 3


def test_file_backed_event_store_replays_after_reconstruction(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    first = EventStore(storage_path=path)
    first.append("session-a", "turn-a", "ready", {"status": "ready"})
    first.append("session-a", "turn-a", "agentMessageCompleted", {"text": "persisted"})

    restarted = EventStore(storage_path=path)
    replay = restarted.replay("session-a", after=0)
    assert [event.sequence for event in replay] == [1, 2]
    assert replay[-1].payload["text"] == "persisted"

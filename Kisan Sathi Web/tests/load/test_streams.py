from __future__ import annotations

import threading
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/harness"))
sys.path.insert(0, str(ROOT / "packages/auth"))


def test_concurrent_event_append_preserves_unique_ordered_cursors(tmp_path: Path):
    from app.event_store import EventStore

    store = EventStore(storage_path=tmp_path / "events.jsonl")
    threads = [threading.Thread(target=lambda i=i: store.append("session-a", "turn-a", "diagnostic", {"worker": i})) for i in range(32)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    replay = store.replay("session-a", after=0)
    assert [event.sequence for event in replay] == list(range(1, 33))


def test_event_store_bounds_retained_bytes(tmp_path: Path):
    from app.event_store import EventStore

    store = EventStore(max_bytes=1024, storage_path=tmp_path / "events.jsonl")
    for index in range(50):
        store.append("session-a", "turn-a", "diagnostic", {"text": "x" * 100, "index": index})
    assert store.json_size("session-a") <= 1024

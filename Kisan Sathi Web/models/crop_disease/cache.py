"""Thread-safe, bounded cache for lazily loaded disease classifiers."""
from __future__ import annotations

from collections import OrderedDict
from threading import Lock, RLock
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class ModelCache(Generic[T]):
    def __init__(self, capacity: int = 2) -> None:
        self.capacity = max(1, capacity)
        self._items: OrderedDict[str, T] = OrderedDict()
        self._lock = RLock()
        self._loading: dict[str, Lock] = {}

    def get_or_load(self, key: str, loader: Callable[[], T]) -> T:
        with self._lock:
            current = self._items.get(key)
            if current is not None:
                self._items.move_to_end(key)
                return current
            load_lock = self._loading.setdefault(key, Lock())
        with load_lock:
            with self._lock:
                current = self._items.get(key)
                if current is not None:
                    self._items.move_to_end(key)
                    return current
            created = loader()
            evicted: list[T] = []
            with self._lock:
                self._items[key] = created
                self._items.move_to_end(key)
                self._loading.pop(key, None)
                while len(self._items) > self.capacity:
                    _, old = self._items.popitem(last=False)
                    evicted.append(old)
            for item in evicted:
                unload = getattr(item, "unload", None)
                if callable(unload):
                    unload()
            return created

    def loaded_ids(self) -> list[str]:
        with self._lock:
            return list(self._items)

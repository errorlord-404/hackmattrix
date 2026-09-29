from models.crop_disease.cache import ModelCache


class Value:
    def __init__(self): self.unloaded = False
    def unload(self): self.unloaded = True


def test_cache_evicts_least_recently_used_item():
    cache = ModelCache[Value](1)
    first, second = Value(), Value()
    assert cache.get_or_load("first", lambda: first) is first
    assert cache.get_or_load("second", lambda: second) is second
    assert first.unloaded and cache.loaded_ids() == ["second"]

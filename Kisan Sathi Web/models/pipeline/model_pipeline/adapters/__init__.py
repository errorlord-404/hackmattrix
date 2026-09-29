"""Optional training/export adapters.

Adapter modules must keep heavyweight framework imports inside callable
boundaries so the registry and release validators stay lightweight.
"""

__all__ = ["pytorch", "tensorflow"]


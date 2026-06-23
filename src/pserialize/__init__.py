"""Public package interface for PSerialization.

PSerialization provides helpers for converting Python objects to primitive
Python data structures and reading those structures back into application
objects.

The main package API exposes the Serializer and Deserializer convenience
classes, along with the lower-level serialize and deserialize functions.
"""

from typing import Any, Callable

from .serialize import serialize
from .deserialize import deserialize


class Serializer:
    """Serialize Python objects using optional type-specific middleware."""

    def __init__(self, middleware: dict[type, Callable[[object], type]] = {}):
        self.middleware = middleware

    def serialize(self, value: Any):
        return serialize(value, self.middleware)


class Deserializer:
    """Deserialize primitive values into typed Python objects."""

    def __init__(self, middleware: dict[type, Callable[[object], type]] = {}):
        self.middleware = middleware

    def deserialize(self, value: Any, classType: type, strict: bool = False):
        return deserialize(value, classType, self.middleware, strict)


__all__ = ["Serializer", "Deserializer", "serialize", "deserialize"]

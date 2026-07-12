"""Public package interface for PSerialization.

PSerialization provides helpers for converting Python objects to primitive
Python data structures and reading those structures back into application
objects.

The main package API exposes the Serializer and Deserializer convenience
classes, along with the lower-level serialize and deserialize functions.
"""

from typing import Any, Callable, Optional

from .serialize import serialize
from .deserialize import (
    MissingRequiredFieldException,
    NullNotAllowedException,
    TypeMismatchException,
    UnknownFieldException,
    UnknownFieldPolicy,
    deserialize,
)


SerializationMiddleware = dict[type, Callable[[object], type]]


class Serializer:
    """Serialize Python objects using optional type-specific middleware."""

    def __init__(self, middleware: Optional[SerializationMiddleware] = None):
        self.middleware = middleware if middleware is not None else {}

    def serialize(self, value: Any):
        return serialize(value, self.middleware)


class Deserializer:
    """Deserialize primitive values into typed Python objects."""

    def __init__(self, middleware: Optional[SerializationMiddleware] = None):
        self.middleware = middleware if middleware is not None else {}

    def deserialize(
        self,
        value: Any,
        classType: type,
        strict: bool = False,
        unknown_fields: Optional[UnknownFieldPolicy] = None,
        coerce: bool = False,
    ):
        return deserialize(
            value,
            classType,
            self.middleware,
            strict,
            unknown_fields,
            coerce,
        )


__all__ = [
    "Serializer",
    "Deserializer",
    "MissingRequiredFieldException",
    "NullNotAllowedException",
    "TypeMismatchException",
    "UnknownFieldException",
    "UnknownFieldPolicy",
    "serialize",
    "deserialize",
]

"""Public package interface for PSerialization.

PSerialization provides helpers for converting Python objects to primitive
Python data structures and reading those structures back into application
objects.
"""

from typing import Any, Optional

from .deserialize import (
    DeserializationContext,
    DeserializationMiddleware,
    DeserializerMiddleware,
    DeserializationMismatch,
    MissingRequiredFieldException,
    NullNotAllowedException,
    TypeMismatchException,
    UnionDeserializationException,
    UnknownFieldException,
    UnknownFieldPolicy,
    deserialize,
)
from .middleware_context import (
    SerializationContext,
    SerializationMiddleware,
    SerializerMiddleware,
)
from .serialize import serialize


class Serializer:
    """Serialize Python objects using optional type-specific middleware."""

    def __init__(
        self,
        middleware: Optional[SerializationMiddleware] = None,
    ):
        self.middleware = dict(middleware) if middleware is not None else {}

    def serialize(self, value: Any):
        return serialize(value, self.middleware)


class Deserializer:
    """Deserialize primitive values into typed Python objects."""

    def __init__(
        self,
        middleware: Optional[DeserializationMiddleware] = None,
    ):
        self.middleware = dict(middleware) if middleware is not None else {}

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
    "SerializationContext",
    "DeserializationContext",
    "SerializerMiddleware",
    "DeserializerMiddleware",
    "SerializationMiddleware",
    "DeserializationMiddleware",
    "DeserializationMismatch",
    "MissingRequiredFieldException",
    "NullNotAllowedException",
    "TypeMismatchException",
    "UnionDeserializationException",
    "UnknownFieldException",
    "UnknownFieldPolicy",
    "serialize",
    "deserialize",
]

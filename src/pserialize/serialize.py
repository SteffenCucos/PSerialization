from collections.abc import Mapping, Sequence, Set
from typing import Any, Optional

from .deserialize import deserialize
from .middleware_context import (
    DeserializationMiddleware,
    SerializationContext,
    SerializationMiddleware,
)
from .serialization_utils import is_enum, is_primitive


_TEXT_LIKE_SEQUENCE_TYPES = (str, bytes, bytearray, memoryview)


class SerializeCycleException(ValueError):
    """Raised when serialization encounters a cyclic object graph."""


class UnsupportedKeyTypeException(ValueError):
    """Raised when a mapping key is not or does not serialize to a string."""

    def __init__(
        self,
        key_type: type,
        serialized_key_type: Optional[type] = None,
    ):
        self.key_type = key_type
        self.serialized_key_type = serialized_key_type

        if serialized_key_type is None:
            detail = f"received {key_type.__name__}"
        else:
            detail = (
                f"key type {key_type.__name__} serialized to "
                f"{serialized_key_type.__name__}"
            )

        super().__init__(f"Mapping keys must be strings; {detail}")


class SerializedKeyCollisionException(ValueError):
    """Raised when distinct mapping keys serialize to the same string."""

    def __init__(self, serialized_key: str):
        self.serialized_key = serialized_key
        super().__init__("Multiple mapping keys serialized to the same string")


def __track_reference(value: object, visited: set[int]) -> int:
    reference = id(value)
    if reference in visited:
        raise SerializeCycleException("Cannot serialize cyclic object graph")
    visited.add(reference)
    return reference


def __serialize_basic_object(
    value: object,
    context: SerializationContext,
    visited: set[int],
) -> dict:
    """Serialize an object using the fields stored in its ``__dict__``."""
    reference = __track_reference(value, visited)
    try:
        return __serialize_dict(vars(value), context, visited)
    finally:
        visited.remove(reference)


def __serialize_dict(
    mapping: Mapping,
    context: SerializationContext,
    visited: set[int],
) -> dict:
    """Serialize a mapping whose keys remain JSON-compatible strings."""
    reference = __track_reference(mapping, visited)
    try:
        serialized = {}
        for key, value in mapping.items():
            if not isinstance(key, str):
                raise UnsupportedKeyTypeException(type(key))

            serialized_key = _serialize_inner(key, context, visited)
            if not isinstance(serialized_key, str):
                raise UnsupportedKeyTypeException(
                    type(key),
                    type(serialized_key),
                )
            if serialized_key in serialized:
                raise SerializedKeyCollisionException(serialized_key)

            serialized[serialized_key] = _serialize_inner(
                value,
                context,
                visited,
            )
        return serialized
    finally:
        visited.remove(reference)


def __serialize_iterable(
    iterable,
    context: SerializationContext,
    visited: set[int],
) -> list:
    """Serialize a sequence or set as a list of serialized elements."""
    reference = __track_reference(iterable, visited)
    try:
        return [
            _serialize_inner(element, context, visited)
            for element in iterable
        ]
    finally:
        visited.remove(reference)


def serialize(
    value: Any,
    middleware: Optional[SerializationMiddleware] = None,
):
    """Serialize a Python value using optional type-specific middleware.

    Mapping keys must be strings and must remain strings after middleware is
    applied. Middleware callables receive ``(value, context)``. The context is
    also a read-only mapping of the registered middleware and exposes
    ``context.serialize(value)`` for recursive serialization with the same
    middleware registry and cycle-detection state.
    """
    if isinstance(middleware, SerializationContext):
        return middleware.serialize(value)

    context = SerializationContext(middleware)
    visited: set[int] = set()
    context._bind(lambda nested: _serialize_inner(nested, context, visited))
    return context.serialize(value)


def _serialize_inner(
    value: Any,
    context: SerializationContext,
    visited: set[int],
):
    class_type = type(value)
    serializer = context.get(class_type)
    if serializer is not None:
        reference = __track_reference(value, visited)
        try:
            return serializer(value, context)
        finally:
            visited.remove(reference)

    if value is None:
        return None
    if is_primitive(class_type):
        return value
    if is_enum(class_type):
        return _serialize_inner(value.value, context, visited)
    if isinstance(value, Mapping):
        return __serialize_dict(value, context, visited)
    if isinstance(value, Sequence) and not isinstance(
        value,
        _TEXT_LIKE_SEQUENCE_TYPES,
    ):
        return __serialize_iterable(value, context, visited)
    if isinstance(value, Set):
        return __serialize_iterable(value, context, visited)

    return __serialize_basic_object(value, context, visited)


def serialize_into(
    value: Any,
    c_type: type,
    s_middleware: Optional[SerializationMiddleware] = None,
    d_middleware: Optional[DeserializationMiddleware] = None,
):
    """Return primitive output after shaping ``value`` through ``c_type``.

    ``serialize_into`` does not return an instance of ``c_type``. It serializes
    ``value``, deserializes that representation as ``c_type``, and serializes the
    converted instance again. ``s_middleware`` is applied during both
    serialization passes, while ``d_middleware`` is applied during conversion.
    """
    serialized = serialize(value, s_middleware)
    custom_type = deserialize(
        serialized,
        c_type,
        d_middleware,
        strict=True,
    )
    return serialize(custom_type, s_middleware)

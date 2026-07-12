from collections.abc import Mapping, Sequence, Set
from typing import Any, Callable, Optional, Union

from .deserialize import deserialize

from .serialization_utils import (
    is_primitive,
    is_enum
)

# Make all methods static
# Make all methods private, except serialize
# Keep serializer class to wrap the static serialize and keep track of middleware


SerializationMiddleware = dict[type, Callable[[object], type]]
_TEXT_LIKE_SEQUENCE_TYPES = (str, bytes, bytearray, memoryview)


class SerializeCycleException(ValueError):
    """Raised when serialization encounters a cyclic object graph."""


def __middleware_or_empty(middleware: Optional[SerializationMiddleware]) -> SerializationMiddleware:
    return middleware if middleware is not None else {}


def __track_reference(value: object, visited: set[int]) -> int:
    reference = id(value)
    if reference in visited:
        raise SerializeCycleException("Cannot serialize cyclic object graph")
    visited.add(reference)
    return reference


def __serialize_basic_object(object: object, middleware: Optional[SerializationMiddleware] = None, visited: Optional[set[int]] = None) -> dict:
    """
    Serializes an object using the fields set on its __dict__

    Args:
        object (object): The object to serialize

    Returns:
        dict: The dict representation of the object
    """
    middleware = __middleware_or_empty(middleware)
    visited = visited if visited is not None else set()
    reference = __track_reference(object, visited)
    try:
        return __serialize_dict(vars(object), middleware, visited)
    finally:
        visited.remove(reference)


def __serialize_dict(mapping: Mapping, middleware: Optional[SerializationMiddleware] = None, visited: Optional[set[int]] = None) -> dict:
    """Serialize a mapping while preserving all entries."""
    middleware = __middleware_or_empty(middleware)
    visited = visited if visited is not None else set()
    reference = __track_reference(mapping, visited)
    try:
        serializedDict = {}
        for key, value in mapping.items():
            serializedKey = _serialize_inner(key, middleware, visited)
            serializedValue = _serialize_inner(value, middleware, visited)
            serializedDict[serializedKey] = serializedValue

        return serializedDict
    finally:
        visited.remove(reference)


def __serialize_iterable(iterable, middleware: Optional[SerializationMiddleware] = None, visited: Optional[set[int]] = None) -> list:
    """Serialize a sequence or set as a list of serialized elements."""
    middleware = __middleware_or_empty(middleware)
    visited = visited if visited is not None else set()
    reference = __track_reference(iterable, visited)
    try:
        serializedList = []
        for element in iterable:
            serializedList.append(_serialize_inner(element, middleware, visited))

        return serializedList
    finally:
        visited.remove(reference)


def serialize(value: Any, middleware: Optional[SerializationMiddleware] = None):
    """
    Serializes an object.

    Default support for:
        Primitives (int, float, str, None)
        Enums
        Mapping implementations and subclasses
        Non-text sequence implementations and subclasses
        Set implementations and subclasses
        Basic objects

    Any custom serialization logic can be added using middleware

    Args:
        value (Any): The value to serialize

    Returns:
        object: The serialized value
    """
    return _serialize_inner(value, __middleware_or_empty(middleware), set())


def _serialize_inner(value: Any, middleware: Optional[SerializationMiddleware] = None, visited: Optional[set[int]] = None):
    middleware = __middleware_or_empty(middleware)
    visited = visited if visited is not None else set()

    classType = type(value)
    if (serializer := middleware.get(classType, None)) is not None:
        return serializer(value, middleware)
    if value is None:
        return None
    if is_primitive(classType):
        return value
    if is_enum(classType):
        return _serialize_inner(value.value, middleware, visited)
    if isinstance(value, Mapping):
        return __serialize_dict(value, middleware, visited)
    if isinstance(value, Sequence) and not isinstance(value, _TEXT_LIKE_SEQUENCE_TYPES):
        return __serialize_iterable(value, middleware, visited)
    if isinstance(value, Set):
        return __serialize_iterable(value, middleware, visited)

    return __serialize_basic_object(value, middleware, visited)


def serialize_into(value: Any, c_type: type, s_middleware: Optional[SerializationMiddleware] = None, d_middleware: Optional[SerializationMiddleware] = None):
    """
    Serializes an object into another object, which may have different field/types.
    Useful for turning a DB object into a DTO

    Args:
        value (Any): The value to serialize
        c_type (type): The desired output type
        deserializer (Deserializer, optional): The deserializer for building the c_type instance. Defaults to default_deserializer.

    Returns:
        c_type: A c_type instance
    """

    serialized = serialize(value, s_middleware)
    # Strict is true here so that we only add the fields defined in c_type to the new object
    custom_type = deserialize(serialized, c_type, d_middleware, strict=True)
    return serialize(custom_type)

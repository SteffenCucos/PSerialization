from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any, Callable, Optional, Protocol


class SerializerMiddleware(Protocol):
    """Callable used to serialize one registered Python type."""

    def __call__(self, value: Any, context: "SerializationContext") -> Any:
        ...


class DeserializerMiddleware(Protocol):
    """Callable used to deserialize one registered Python type."""

    def __call__(self, value: Any, context: "DeserializationContext") -> Any:
        ...


SerializationMiddleware = Mapping[type, SerializerMiddleware]
DeserializationMiddleware = Mapping[type, DeserializerMiddleware]


class SerializationContext(Mapping[type, SerializerMiddleware]):
    """Middleware registry plus recursive serialization access."""

    def __init__(
        self,
        middleware: Optional[SerializationMiddleware] = None,
    ):
        self._middleware = dict(middleware) if middleware is not None else {}
        self._serialize_callback: Optional[Callable[[Any], Any]] = None

    def _bind(self, callback: Callable[[Any], Any]) -> None:
        self._serialize_callback = callback

    def serialize(self, value: Any) -> Any:
        if self._serialize_callback is None:
            raise RuntimeError("SerializationContext is not bound to a serializer")
        return self._serialize_callback(value)

    @property
    def middleware(self) -> Mapping[type, SerializerMiddleware]:
        return self._middleware

    def __getitem__(self, key: type) -> SerializerMiddleware:
        return self._middleware[key]

    def __iter__(self) -> Iterator[type]:
        return iter(self._middleware)

    def __len__(self) -> int:
        return len(self._middleware)


class DeserializationContext(Mapping[type, DeserializerMiddleware]):
    """Middleware registry plus recursive deserialization configuration."""

    def __init__(
        self,
        middleware: Optional[DeserializationMiddleware] = None,
        *,
        unknown_fields: str = "reject",
        coerce: bool = False,
    ):
        self._middleware = dict(middleware) if middleware is not None else {}
        self._deserialize_callback: Optional[Callable[[Any, type], Any]] = None
        self.unknown_fields = unknown_fields
        self.coerce = coerce

    def _bind(self, callback: Callable[[Any, type], Any]) -> None:
        self._deserialize_callback = callback

    def deserialize(self, value: Any, target_type: type) -> Any:
        if self._deserialize_callback is None:
            raise RuntimeError("DeserializationContext is not bound to a deserializer")
        return self._deserialize_callback(value, target_type)

    @property
    def middleware(self) -> Mapping[type, DeserializerMiddleware]:
        return self._middleware

    def __getitem__(self, key: type) -> DeserializerMiddleware:
        return self._middleware[key]

    def __iter__(self) -> Iterator[type]:
        return iter(self._middleware)

    def __len__(self) -> int:
        return len(self._middleware)


__all__ = [
    "SerializerMiddleware",
    "DeserializerMiddleware",
    "SerializationMiddleware",
    "DeserializationMiddleware",
    "SerializationContext",
    "DeserializationContext",
]

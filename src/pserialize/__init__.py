
from typing import Any, Callable

from .serialize import serialize, serialize_into
from .deserialize import deserialize


class Serializer:
    def __init__(self, middleware: dict[type, Callable[[object], type]] = {}):
        self.middleware = middleware

    def serialize(self, value):
        return serialize(value, self.middleware)


class Deserializer:
    def __init__(self, middleware: dict[type, Callable[[object], type]] = {}):
        self.middleware = middleware

    def deserialize(self, value: Any, classType: type, strict: bool = False):
        return deserialize(value, classType, self.middleware, strict)
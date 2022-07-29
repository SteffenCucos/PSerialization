
from typing import Any, Callable

from .serialization_utils import (
    is_primitive,
    is_enum
)


class Serializer:
    def __init__(self, middleware: dict[type, Callable[[object], type]] = []):
        self.middleware = middleware

    def serialize_basic_object(self, object: object) -> dict:
        return self.serialize_dict(vars(object))

    def serialize_dict(self, dict: dict) -> dict:
        serializedDict = {}
        for key, value in dict.items():
            serializedKey = self.serialize(key)
            serializedValue = self.serialize(value)
            serializedDict[serializedKey] = serializedValue

        return serializedDict

    def serialize_list(self, list: list) -> list:
        serializedList = []
        for element in list:
            serializedList.append(self.serialize(element))

        return serializedList

    def serialize(self, value: Any):
        if value is None:
            return None
        classType = type(value)
        if is_primitive(classType):
            return value
        if is_enum(classType):
            # Represent enums as their String representation
            return self.serialize(value.value)
        if classType is list:
            return self.serialize_list(value)
        if classType is dict:
            return self.serialize_dict(value)
        if (serializer := self.middleware.get(classType, None)) is not None:
            return serializer(value)

        return self.serialize_basic_object(value)


default_serializer = Serializer(middleware={})


from typing import Any, Callable

from src.pserialize.deserialize import Deserializer, default_deserializer

from .serialization_utils import (
    is_primitive,
    is_enum
)


class Serializer:
    def __init__(self, middleware: dict[type, Callable[[object], type]] = []):
        self.middleware = middleware

    def serialize_basic_object(self, object: object) -> dict:
        """
        Serializes an object using the fields set on its __dict__

        Args:
            object (object): The object to serialize

        Returns:
            dict: The dict representation of the object
        """
        
        return self.serialize_dict(vars(object))

    def serialize_dict(self, dict: dict) -> dict:
        """
        Serializes a dictionary

        Args:
            dict (dict): The dictionary to serialize

        Returns:
            dict: The serialized dictionary
        """

        serializedDict = {}
        for key, value in dict.items():
            serializedKey = self.serialize(key)
            serializedValue = self.serialize(value)
            serializedDict[serializedKey] = serializedValue

        return serializedDict

    def serialize_list(self, list: list) -> list:
        """
        Serializes a list of objects

        Args:
            list (list): The list to serialize

        Returns:
            list: The serialized list
        """
        serializedList = []
        for element in list:
            serializedList.append(self.serialize(element))

        return serializedList

    def serialize(self, value: Any):
        """
        Serializes an object.
        
        Default support for:
            Primitives (int, float, str, None)
            Enums
            Lists
            Dicts
            Basic objects

        Any custom serialization logic can be added using middleware

        Args:
            value (Any): The value to serialize

        Returns:
            object: The serialized value
        """

        classType = type(value)
        if (serializer := self.middleware.get(classType, None)) is not None:
            return serializer(self, value)
        if value is None:
            return None
        if is_primitive(classType):
            return value
        if is_enum(classType):
            return self.serialize(value.value)
        if classType is list:
            return self.serialize_list(value)
        if classType is dict:
            return self.serialize_dict(value)

        return self.serialize_basic_object(value)

    def serialize_into(self, value: Any, c_type: type, deserializer: Deserializer = default_deserializer):
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

        serialized = self.serialize(value)
        custom_type = deserializer.deserialize(serialized, c_type, strict=True)
        return self.serialize(custom_type)


default_serializer = Serializer(middleware={})

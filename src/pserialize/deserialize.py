from typing import (
    Any,
    Callable,
    Type,
    get_type_hints
)

# https://docs.python.org/3/library/types.html#:~:text=class%20types.-,GenericAlias,-(t_origin%2C%20t_args)%C2%B6
# GenericAlias is the type used for parameterized lists and dicts
# ie: list[int], dict[str,object], etc
from types import GenericAlias
from enum import Enum

import dataclasses

from .serialization_utils import (
    is_primitive,
    is_enum,
    is_optional,
    is_union,
    get_attributes
)


class Deserializer:
    def __init__(self, middleware: dict[type, Callable[[object], type]] = []):
        self.middleware = middleware

    def deserialize_enum(self, value: Any, enumType: Type[Enum]) -> Enum:
        """
        Deserializes a value into an Enum

        Args:
            value (Any): The value to deserialize
            enumType (Type[Enum]): The specific Enum type to create

        Returns:
            Enum: The deserialized value
        """

        return enumType(value)

    def deserialize_simple_object(self, dict: dict, classType: type, strict: bool = False):
        """
        Constructs an instance of the given type from the supplied dictionary

        Args:
            dict (dict): Dictionary with object structure
            classType (type): The type to deserialize into
            strict (bool, optional): Determines if extra fields in the dictionary that are not found in the type should be inserted into the object. Defaults to False.

        Returns:
            classType: An instance of classType
        """

        attributes = get_attributes(classType)

        type_hints = get_type_hints(classType.__init__)
        if dataclasses.is_dataclass(classType):
            type_hints.pop("return", None)

        # Create an empty instance of classType
        # Some types (ex: datetime.datetime) prohibit this call
        # and will need a custom deserializer
        cls = object.__new__(classType)

        # Serialize any field that we can find a type hint for,
        # otherwise set it to the raw primitive value
        for name, value in dict.items():
            # Check if an attribute with the given name exists, but overwrite
            # the type if it exists in the constructor type_hints
            type = attributes.pop(name) if name in attributes.keys() else None
            type = type_hints.pop(name) if name in type_hints.keys() else type

            # if strict deserialization is set, then we want to skip deserializing
            # fields that we can't find a type for
            if strict and type is None:
                continue

            cls.__dict__[name] = self.deserialize(value, type, strict) if type else value

        if len(attributes.keys()) + len(type_hints.keys()) > 0:
            # There are attributes or init_parameters that weren't found in the dictionary
            pass

        return cls

    def deserialize_list(self, lst: list, classType: type, strict: bool = False):
        """
        Deserializes a list[classType]

        Args:
            lst (list): The list to deserialize
            classType (type): The type of the list elements
            strict (bool, optional): Determines if extra fields will/won't be added to the deserialized value. Defaults to False.

        Returns:
            list[classType]: Deserialized list of elements
        """

        deserializedList = []
        for value in lst:
            deserializedList.append(self.deserialize(value, classType, strict))

        return deserializedList

    def deserialize_dict(self, dict: dict, keyType: type, valueType: type, strict: bool = False):
        """
        Deserializes the keys and values of the input dictionary

        Args:
            dict (dict): The dictionary to deserialize
            keyType (type): The type of the keys of the dictionary
            valueType (type): The type of the values of the dictionary
            strict (bool, optional): Determines if extra fields will/won't be added to the deserialized value. Defaults to False.

        Returns:
            dict[keyType, valueType]: Deserialized dictionary
        """

        deserializedDict = {}
        for key, value in dict.items():
            deserializedKey = self.deserialize(key, keyType, strict)
            deserializedValue = self.deserialize(value, valueType, strict)
            deserializedDict[deserializedKey] = deserializedValue

        return deserializedDict

    def deserialize_union(self, value: Any, allowed_types: list[type], strict: bool = False):
        """
        Deserializes a value into the first allowed type that succeeds

        Args:
            value (Any): The value to deserialize
            allowed_types (list[type]): The list of possible types the value represents
            strict (bool, optional): Determines if extra fields will/won't be added to the deserialized value. Defaults to False.

        Returns:
            type: An instance of one of the allowed types
        """

        for type in allowed_types:
            try:
                # Check each type from left to right and return
                # the first deserialized value that works
                return self.deserialize(value, type, strict)
            except Exception:
                pass

    def deserialize(self, value: Any, classType: type, strict: bool = False):
        """
        Deserializes an arbitrary value into the supplied class type

        Args:
            value (Any): The value to deserialize
            classType (type): The type the value represents
            strict (bool, optional): Determines if extra fields will/won't be added to the deserialized value. Defaults to False.

        Returns:
            classType: An instance of classType
        """

        if value is None:
            # Allow None values
            return None
        if is_primitive(classType):
            return classType(value)
        if is_enum(classType):
            return classType(value)
        if is_optional(classType):
            # If the parameter is optional, unpack the optional type and deserialize that type
            realType = classType.__args__[0]
            return self.deserialize(value, realType)
        if isinstance(classType, GenericAlias):
            typeArgs = classType.__args__
            originType = classType.__origin__
            if originType is list:  # list of some type
                typeArg = typeArgs[0]  # List parameterization only takes 1 argument
                return self.deserialize_list(value, typeArg, strict)
            else:
                keyType = typeArgs[0]
                valueType = typeArgs[1]
                return self.deserialize_dict(value, keyType, valueType, strict)
        if is_union(classType):
            allowed_types = classType.__args__
            return self.deserialize_union(value, allowed_types, strict)
        if (deserializer := self.middleware.get(classType, None)) is not None:
            return deserializer(value)

        return self.deserialize_simple_object(value, classType, strict)


default_deserializer = Deserializer(middleware={})
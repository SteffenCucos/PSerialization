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
    get_attributes
)


class Deserializer:
    def __init__(self, middleware: dict[type, Callable[[object], type]] = []):
        self.middleware = middleware

    def deserialize_enum(self, v: Any, enumType: Type[Enum]) -> Enum:
        return enumType(v)

    def deserialize_simple_object(self, d: dict, classType: type):
        '''
        Constructs an instance of the given type from the supplied dictionary.

        Any field in the dict that has no corresponding type will be set on
        the object as its raw value.

        Currently does not support Union types
        '''
        attributes = get_attributes(classType)

        type_hints = get_type_hints(classType.__init__)
        if dataclasses.is_dataclass(classType):
            type_hints.pop("return", None)

        # Create an empty instance of classType
        # Some types (ex: datetime.datetime) prohibit this call
        # and will need a custom deserializer
        cls = object.__new__(classType)

        # Sereialize any field that we can find a type hint for,
        # otherwise set it to the raw primitve value
        for name, value in d.items():
            # Check if an attribute with the given name exists, but overrite
            # the type if it exists in the constructor type_hints
            type = attributes.pop(name) if name in attributes.keys() else None
            type = type_hints.pop(name) if name in type_hints.keys() else type
            cls.__dict__[name] = self.deserialize(value, type) if type else value

        if len(attributes.keys()) + len(type_hints.keys()) > 0:
            # There are attributes or init_parameters that weren't found in the dictionary
            pass

        return cls

    def deserialize_list(self, lst: list, classType: type):
        deserializedList = []
        for value in lst:
            deserializedList.append(self.deserialize(value, classType))

        return deserializedList

    def deserialize_dict(self, d: dict, keyType: type, valueType: type):
        deserializedDict = {}
        for key, value in d.items():
            deserializedKey = self.deserialize(key, keyType)
            deserializedValue = self.deserialize(value, valueType)
            deserializedDict[deserializedKey] = deserializedValue

        return deserializedDict

    def deserialize(self, value: Any, classType: type):
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
                typeArg = typeArgs[0]  # List paramaterization only takes 1 argument
                return self.deserialize_list(value, typeArg)
            else:
                keyType = typeArgs[0]
                valueType = typeArgs[1]
                return self.deserialize_dict(value, keyType, valueType)
        if (deserializer := self.middleware.get(classType, None)) is not None:
            return deserializer(value)

        return self.deserialize_simple_object(value, classType)


default_deserializer = Deserializer(middleware={})

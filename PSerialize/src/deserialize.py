from typing import (
    Any,
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
    is_optional
)

def deserialize_enum(v: Any, enumType: Type[Enum]) -> Enum:
    return enumType(v)

def deserialize_object(d: dict, classType: type):
    init = classType.__init__
    hints = get_type_hints(init)

    if dataclasses.is_dataclass(classType):
        hints.pop("return", None)

    arguments = set(init.__code__.co_varnames)
    # Calling the constructor instead of init will handle self
    arguments.remove("self")

    if len(hints) < len(arguments):
        return "All parameters must be typed"

    if len(d) < len(hints):
        return "Not enough parameters in dict"

    deserializedParameters = {}
    for varName, varType in hints.items():
        value = d.get(varName)
        deserializedValue = deserialize(value, varType)
        deserializedParameters[varName] = deserializedValue
        
    return classType(** deserializedParameters)

def deserialize_list(l: list, classType: type):
    deserializedList = []
    for value in l:
        deserializedList.append(deserialize(value, classType))

    return deserializedList

def deserialize_dict(d: dict, keyType: type, valueType: type):
    deserializedDict = {}
    for key, value in d.items():
        deserializedKey = deserialize(key, keyType)
        deserializedValue = deserialize(value, valueType)
        deserializedDict[deserializedKey] = deserializedValue

    return deserializedDict
    
def deserialize(value: Any, classType: type):
    if value == None:
        # Allow None values
        return None
    if is_primitive(classType):
        return classType(value)
    if is_enum(classType):
        return classType(value)
    if is_optional(classType):
        # If the parameter is optional, unpack the optional type and deserialize that type
        realType = classType.__args__[0]
        return deserialize(value, realType)
    if isinstance(classType, GenericAlias):
        typeArgs = classType.__args__
        originType = classType.__origin__
        if originType == type([]): # list of some type
            typeArg = typeArgs[0] # List paramaterization only takes 1 argument
            return deserialize_list(value, typeArg)
        else:
            keyType = typeArgs[0]
            valueType = typeArgs[1]
            return deserialize_dict(value, keyType, valueType)
    else:
        return deserialize_object(value, classType)
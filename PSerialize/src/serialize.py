
from typing import Any

from .serialization_utils import (
    is_primitive,
    is_enum
)

def serialize_object(object: object) -> dict:
    return serialize_dict(vars(object))

def serialize_dict(dict: dict) -> dict:
    serializedDict = {}
    for key, value in dict.items():
        serializedKey = serialize(key)
        serializedValue = serialize(value)
        serializedDict[serializedKey] = serializedValue

    return serializedDict

def serialize_list(list: list) -> list:
    serializedList = []
    for element in list:
        serializedList.append(serialize(element))
    
    return serializedList

def serialize(value: Any):
    if value == None:
        return None
    classType = type(value)
    if is_primitive(classType):
        return value
    if is_enum(classType):
        # Represent enums as their String representation
        return serialize(value.value)
    if classType is type([]):
        return serialize_list(value)
    if classType is type({}):
        return serialize_dict(value)
    return serialize_object(value)
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

def get_type_hierarchy(classType: type):
    '''
    Returns the type hierarchy in method/variable resolution order

        A
        /\----\
       B  C    H
       |  |    |
       D  |    G
         /\
        E  F

    becomes
    [A, B, D, C, E, F, H, G]   
    '''
    def get_bases(classType: type):
        bases = [base for base in classType.__bases__ if base != object]
        bases.reverse()
        return bases

    typeHierarchy = [classType]
    bases = get_bases(classType)

    while len(bases) > 0:
        base = bases.pop()
        typeHierarchy.append(base)
        
        for base in get_bases(base):
            bases.append(base)

    return typeHierarchy

def get_attributes(classType: type) -> dict[str, type]:
    attributes = {}
    # Use the python defined method/variable resolution order to get the correct type for each attribute
    for type in get_type_hierarchy(classType):
        for attrName, attrType in getattr(type, '__annotations__', {}).items():
            if attrName not in attributes.keys():
                attributes[attrName] = attrType
    
    return attributes

def get_empty_constructor():
    def __init__(self):
        pass

    return __init__

def deserialize_object(d: dict, classType: type):
    '''
    Constructs an instance of the given type from the supplied dictionary.

    Any field in the dict that has no corresponding type will be set on
    the object as its raw value.

    Currently does not support Union types
    '''
    # Avoid running the constructor by forcing an
    # empty init function to run instead of the real init.
    # This avoids any potential stateful code from running
    # Think some field on the object that sets a value based
    # on the day of the week
    class_init = classType.__init__
    classType.__init__ = get_empty_constructor()
    cls = classType()
    classType.__init__ = class_init

    attributes = get_attributes(classType)

    type_hints = get_type_hints(class_init)
    if dataclasses.is_dataclass(classType):
        type_hints.pop("return", None)

    # Sereialize any field that we can find a type hint for,
    # otherwise set it to the raw primitve value
    for name, value in d.items():
        # Check if an attribute with the given name exists, but overrite 
        # the type if it exists in the constructor type_hints
        type = attributes.pop(name) if name in attributes.keys() else None
        type = type_hints.pop(name) if name in type_hints.keys() else type
        cls.__dict__[name] = deserialize(value, type) if type else value

    return cls

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
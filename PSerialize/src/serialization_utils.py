
from typing import (
    Union,
    get_args,
    get_origin
)

from enum import Enum

import inspect

primitiveTypes = set([bool, int, float, str])


def is_primitive(type: type):
    return type in primitiveTypes or is_extended_primitive(type)


def is_extended_primitive(type: type):
    if not inspect.isclass(type):
        return False
    for primitive in primitiveTypes:
        if issubclass(type, primitive):
            return True
    return False


def is_enum(type: type):
    return inspect.isclass(type) and issubclass(type, Enum)


def is_optional(typeT: type):
    origin = get_origin(typeT)
    args = get_args(typeT)
    return origin is Union and type(None) in args


def get_type_hierarchy(classType: type):
    '''
    Returns the type hierarchy in method/variable resolution order

         A
        / |----\
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

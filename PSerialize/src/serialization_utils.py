
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

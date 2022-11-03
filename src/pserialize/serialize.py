
from typing import Any, Callable

from .deserialize import deserialize

from .serialization_utils import (
    is_primitive,
    is_enum
)

# Make all methods static
# Make all methods private, except serialize
# Keep serializer class to wrap the static serialize and keep track of middleware


def __serialize_basic_object(object: object, middleware: dict[type, Callable[[object], type]] = {}) -> dict:
    """
    Serializes an object using the fields set on its __dict__

    Args:
        object (object): The object to serialize

    Returns:
        dict: The dict representation of the object
    """
    
    return __serialize_dict(vars(object), middleware)

def __serialize_dict(dict: dict, middleware: dict[type, Callable[[object], type]] = {}) -> dict:
    """
    Serializes a dictionary

    Args:
        dict (dict): The dictionary to serialize

    Returns:
        dict: The serialized dictionary
    """

    serializedDict = {}
    for key, value in dict.items():
        serializedKey = serialize(key, middleware)
        serializedValue = serialize(value, middleware)
        serializedDict[serializedKey] = serializedValue

    return serializedDict

def __serialize_list(list: list, middleware: dict[type, Callable[[object], type]] = {}) -> list:
    """
    Serializes a list of objects

    Args:
        list (list): The list to serialize

    Returns:
        list: The serialized list
    """
    serializedList = []
    for element in list:
        serializedList.append(serialize(element, middleware))

    return serializedList

def serialize(value: Any, middleware: dict[type, Callable[[object], type]] = {}):
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
    if (serializer := middleware.get(classType, None)) is not None:
        return serializer(value, middleware)
    if value is None:
        return None
    if is_primitive(classType):
        return value
    if is_enum(classType):
        return serialize(value.value, middleware)
    if classType is list:
        return __serialize_list(value, middleware)
    if classType is dict:
        return __serialize_dict(value, middleware)

    return __serialize_basic_object(value, middleware)

def serialize_into(value: Any, c_type: type, s_middleware: dict[type, Callable[[object], type]] = {}, d_middleware: dict[type, Callable[[object], type]] = {}):
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

    serialized = serialize(value, s_middleware)
    # Strict is true here so that we only add the fields defined in c_type to the new object
    custom_type = deserialize(serialized, c_type, d_middleware, strict=True)
    return serialize(custom_type)

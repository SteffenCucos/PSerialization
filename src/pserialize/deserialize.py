import dataclasses
from enum import Enum
# https://docs.python.org/3/library/types.html#:~:text=class%20types.-,GenericAlias,-(t_origin%2C%20t_args)%C2%B6
# GenericAlias is the type used for parameterized lists and dicts
# ie: list[int], dict[str,object], etc
from types import GenericAlias
from typing import Any, Callable, Type, Union, get_type_hints

from .serialization_utils import (get_attributes, is_enum, is_optional,
                                  is_primitive, is_union)


def type_args_string(type: type):
    if is_union(type):
        name = "Union"
    elif hasattr(type, "__name__"):
        name = type.__name__ 
    else:
        name = str(type)

    if not hasattr(type, "__args__") or len(type.__args__) == 0:
        return name
    return f"{name}[{', '.join([type_args_string(arg) for arg in type.__args__])}]"

@dataclasses.dataclass
class BaseDeserializationException(Exception):
    error: Exception
    value: Any

    def __repr__(self):
        s = ""
        if isinstance(self.error, BaseDeserializationException):
            s += " -> " + str(self.error)
        else:
            s += f"'{self.value}' |{str(self.error)}|"
        
        return s

    def __str__(self):
        return self.__repr__()

@dataclasses.dataclass
class DeserializeDictKeyException(BaseDeserializationException):
    keyType: type
    valueType: type

    def __repr__(self):
        return f"dict[{type_args_string(self.keyType)},{type_args_string(self.valueType)}].key" + super().__repr__()

@dataclasses.dataclass
class DeserializeDictValueException(BaseDeserializationException):
    keyType: type
    valueType: type
    key: Any

    def __repr__(self):
        return f"dict[{type_args_string(self.keyType)},{type_args_string(self.valueType)}].value" + super().__repr__()

@dataclasses.dataclass
class DeserializeListException(BaseDeserializationException):
    itemType: type
    index: int

    def __repr__(self):
        return f"{type_args_string(self.itemType)}[{self.index}]" + super().__repr__()

@dataclasses.dataclass
class DeserializeClassException(BaseDeserializationException):
    field_type: type
    field_name: str 

    def __repr__(self):
        # Get the type of the field
        s = ""
        if self.field_name:
            s += self.field_name + ":"
        
        if isinstance(self.error, (DeserializeListException, DeserializeDictKeyException, DeserializeDictValueException)):
            # list errors report a more complete type 
            s += self.error.__repr__()
        else:
            s += type_args_string(self.field_type) + super().__repr__()

        return s

type_of = type

def __deserialize_simple_object(dict: dict, classType: type, middleware: dict[type, Callable[[object], type]] = {}, strict: bool = False):
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
        
        try:
            cls.__dict__[name] = __deserialize_inner(value, type, middleware, strict) if type else value
        except Exception as e:
            raise DeserializeClassException(e, value, type, name)

    if len(attributes.keys()) + len(type_hints.keys()) > 0:
        # There are attributes or init_parameters that weren't found in the dictionary
        pass

    return cls

def __deserialize_list(lst: list, listType: list[type], middleware: dict[type, Callable[[object], type]] = {}, strict: bool = False):
    """
    Deserializes a list[classType]

    Args:
        lst (list): The list to deserialize
        classType (type): The type of the list elements
        strict (bool, optional): Determines if extra fields will/won't be added to the deserialized value. Defaults to False.

    Returns:
        list[classType]: Deserialized list of elements
    """
    typeArgs = listType.__args__
    typeArg = typeArgs[0]  # List parameterization only takes 1 argument

    deserializedList = []
    for index in range(len(lst)):
        value = lst[index]
        try:
            deserializedList.append(__deserialize_inner(value, typeArg, middleware, strict))
        except Exception as e:
            raise DeserializeListException(e, value, listType, index)


    return deserializedList

def __deserialize_dict(dict: dict, keyType: type, valueType: type, middleware: dict[type, Callable[[object], type]] = {}, strict: bool = False):
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
        try:
            deserializedKey = __deserialize_inner(key, keyType, middleware, strict)
        except Exception as e:
            raise DeserializeDictKeyException(e, key, keyType, valueType)

        try:
            deserializedValue = __deserialize_inner(value, valueType, middleware, strict)
        except Exception as e:
            raise DeserializeDictValueException(e, value, keyType, valueType, key)

        deserializedDict[deserializedKey] = deserializedValue

    return deserializedDict

def __deserialize_union(value: Any, allowed_types: list[type], middleware: dict[type, Callable[[object], type]] = {}, strict: bool = False):
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
            return __deserialize_inner(value, type, middleware, strict)
        except Exception:
            pass

    raise BaseDeserializationException(Exception("Could not deserialize union"), value)

def deserialize(value: Any, classType: type, middleware: dict[type, Callable[[object], type]] = {}, strict: bool = False):
    """
    Deserializes an arbitrary value into the supplied class type

    Default support for:
        Primitives (int, float, str, None)
        Enums
        Lists
        Dicts
        Basic objects

    Any custom deserialization logic can be added using middleware

    Args:
        value (Any): The value to deserialize
        classType (type): The type the value represents
        strict (bool, optional): Determines if extra fields will/won't be added to the deserialized value. Defaults to False.

    Returns:
        classType: An instance of classType
    """

    try:
        return __deserialize_inner(value, classType, middleware, strict)
    except Exception as e:
        raise DeserializeClassException(e, value, classType, None)

def __deserialize_inner(value: Any, classType: type, middleware: dict[type, Callable[[object], type]] = {}, strict: bool = False):
    def deserialize_primitive(classType: type, value: Any):
        try:
            return classType(value)
        except Exception as e:
            raise BaseDeserializationException(e, value)
            #raise f" = '{value}' |{str(e)}|"

    if (deserializer := middleware.get(classType, None)) is not None:
        return deserializer(value, middleware)
    if value is None:
        # Allow None values
        return None
    if is_primitive(classType):
        return deserialize_primitive(classType, value)
    if is_enum(classType):
        return deserialize_primitive(classType, value)
    if is_optional(classType):
        # If the parameter is optional, unpack the optional type and deserialize that type
        realType = classType.__args__[0]
        return __deserialize_inner(value, realType, middleware, strict)
    if isinstance(classType, GenericAlias):
        typeArgs = classType.__args__
        originType = classType.__origin__
        if originType is list:  # list of some type
            typeArg = typeArgs[0]  # List parameterization only takes 1 argument
            return __deserialize_list(value, classType, middleware, strict)
        else:
            keyType = typeArgs[0]
            valueType = typeArgs[1]
            return __deserialize_dict(value, keyType, valueType, middleware, strict)
    if is_union(classType):
        allowed_types = classType.__args__
        return __deserialize_union(value, allowed_types, middleware, strict)

    return __deserialize_simple_object(value, classType, middleware, strict)

import dataclasses
from types import GenericAlias
from typing import Any, Callable, get_type_hints

from .serialization_utils import get_attributes, is_enum, is_optional, is_primitive, is_union


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
        s = ""
        if self.field_name:
            s += self.field_name + ":"
        if isinstance(self.error, (DeserializeListException, DeserializeDictKeyException, DeserializeDictValueException)):
            s += self.error.__repr__()
        else:
            s += type_args_string(self.field_type) + super().__repr__()
        return s


def __deserialize_simple_object(data: dict, classType: type, middleware: dict[type, Callable[[object], type]] = {}, strict: bool = False):
    attributes = get_attributes(classType)
    type_hints = get_type_hints(classType.__init__)
    if dataclasses.is_dataclass(classType):
        type_hints.pop("return", None)

    cls = object.__new__(classType)

    for name, value in data.items():
        field_type = attributes.pop(name) if name in attributes.keys() else None
        field_type = type_hints.pop(name) if name in type_hints.keys() else field_type

        if strict and field_type is None:
            continue

        try:
            cls.__dict__[name] = __deserialize_inner(value, field_type, middleware, strict) if field_type else value
        except Exception as e:
            raise DeserializeClassException(e, value, field_type, name)

    remaining = [name for name in attributes.keys()] + [name for name in type_hints.keys()]
    for field in remaining:
        cls.__dict__[field] = None

    return cls


def __deserialize_collection_items(values, collectionType: type, itemType: type, middleware: dict[type, Callable[[object], type]] = {}, strict: bool = False):
    deserialized = []
    for index in range(len(values)):
        value = values[index]
        try:
            deserialized.append(__deserialize_inner(value, itemType, middleware, strict))
        except Exception as e:
            raise DeserializeListException(e, value, collectionType, index)
    return deserialized


def __deserialize_list(values: list, listType: list[type], middleware: dict[type, Callable[[object], type]] = {}, strict: bool = False):
    typeArg = listType.__args__[0]
    return __deserialize_collection_items(values, listType, typeArg, middleware, strict)


def __deserialize_tuple(values: list, tupleType: tuple[type], middleware: dict[type, Callable[[object], type]] = {}, strict: bool = False):
    typeArgs = tupleType.__args__
    if len(typeArgs) == 2 and typeArgs[1] is Ellipsis:
        return tuple(__deserialize_collection_items(values, tupleType, typeArgs[0], middleware, strict))

    if len(values) != len(typeArgs):
        raise BaseDeserializationException(Exception(f"Expected tuple of length {len(typeArgs)}, got {len(values)}"), values)

    deserialized = []
    for index, typeArg in enumerate(typeArgs):
        try:
            deserialized.append(__deserialize_inner(values[index], typeArg, middleware, strict))
        except Exception as e:
            raise DeserializeListException(e, values[index], tupleType, index)
    return tuple(deserialized)


def __deserialize_set(values: list, setType: set[type], middleware: dict[type, Callable[[object], type]] = {}, strict: bool = False):
    typeArg = setType.__args__[0]
    return set(__deserialize_collection_items(values, setType, typeArg, middleware, strict))


def __deserialize_frozenset(values: list, frozenSetType: frozenset[type], middleware: dict[type, Callable[[object], type]] = {}, strict: bool = False):
    typeArg = frozenSetType.__args__[0]
    return frozenset(__deserialize_collection_items(values, frozenSetType, typeArg, middleware, strict))


def __deserialize_dict(data: dict, keyType: type, valueType: type, middleware: dict[type, Callable[[object], type]] = {}, strict: bool = False):
    deserializedDict = {}
    for key, value in data.items():
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
    value_type = type(value)
    for allowed_type in allowed_types:
        if value_type is allowed_type:
            return value

    for allowed_type in allowed_types:
        try:
            return __deserialize_inner(value, allowed_type, middleware, strict)
        except Exception:
            pass

    raise BaseDeserializationException(Exception("Could not deserialize union"), value)


def deserialize(value: Any, classType: type, middleware: dict[type, Callable[[object], type]] = {}, strict: bool = False):
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

    if (deserializer := middleware.get(classType, None)) is not None:
        return deserializer(value, middleware)
    if value is None:
        return None
    if is_primitive(classType):
        return deserialize_primitive(classType, value)
    if is_enum(classType):
        return deserialize_primitive(classType, value)
    if is_optional(classType):
        realType = classType.__args__[0]
        return __deserialize_inner(value, realType, middleware, strict)
    if isinstance(classType, GenericAlias):
        typeArgs = classType.__args__
        originType = classType.__origin__
        if originType is list:
            return __deserialize_list(value, classType, middleware, strict)
        if originType is tuple:
            return __deserialize_tuple(value, classType, middleware, strict)
        if originType is set:
            return __deserialize_set(value, classType, middleware, strict)
        if originType is frozenset:
            return __deserialize_frozenset(value, classType, middleware, strict)
        if originType is dict:
            keyType = typeArgs[0]
            valueType = typeArgs[1]
            return __deserialize_dict(value, keyType, valueType, middleware, strict)
    if is_union(classType):
        return __deserialize_union(value, classType.__args__, middleware, strict)

    return __deserialize_simple_object(value, classType, middleware, strict)

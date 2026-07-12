import dataclasses
import inspect
from typing import Any, Callable, Literal, Optional, get_args, get_origin, get_type_hints

from .serialization_utils import get_attributes, is_enum, is_optional, is_primitive, is_union


DeserializationMiddleware = dict[type, Callable[[object], type]]
UnknownFieldPolicy = Literal["reject", "ignore", "preserve"]
_VALID_UNKNOWN_FIELD_POLICIES = {"reject", "ignore", "preserve"}


def __middleware_or_empty(middleware: Optional[DeserializationMiddleware]) -> DeserializationMiddleware:
    return middleware if middleware is not None else {}


def __resolve_unknown_field_policy(
    strict: bool,
    unknown_fields: Optional[UnknownFieldPolicy],
) -> UnknownFieldPolicy:
    if unknown_fields is None:
        # Backward compatibility: strict=True historically ignored fields that
        # were not declared by the target type. The safer default for new calls
        # is to reject unknown fields.
        return "ignore" if strict else "reject"

    if unknown_fields not in _VALID_UNKNOWN_FIELD_POLICIES:
        allowed = ", ".join(sorted(_VALID_UNKNOWN_FIELD_POLICIES))
        raise ValueError(f"unknown_fields must be one of: {allowed}")

    return unknown_fields


def __is_literal(type_hint: type) -> bool:
    return get_origin(type_hint) is Literal


def __is_type_var(type_hint: type) -> bool:
    return hasattr(type_hint, "__constraints__") and hasattr(type_hint, "__bound__")


def __literal_matches(value: Any, literal_value: Any) -> bool:
    return value == literal_value and type(value) is type(literal_value)


def __allows_none(type_hint: type) -> bool:
    if type_hint is Any or type_hint is type(None):
        return True

    if __is_literal(type_hint):
        return any(literal_value is None for literal_value in get_args(type_hint))

    if __is_type_var(type_hint):
        constraints = getattr(type_hint, "__constraints__", ())
        if constraints:
            return any(__allows_none(constraint) for constraint in constraints)

        bound = getattr(type_hint, "__bound__", None)
        return bound is None or __allows_none(bound)

    return is_union(type_hint) and type(None) in get_args(type_hint)


def type_args_string(type: type):
    if is_union(type):
        name = "Union"
    elif __is_literal(type):
        name = "Literal"
    elif __is_type_var(type):
        name = getattr(type, "__name__", str(type))
    elif hasattr(type, "__name__"):
        name = type.__name__
    else:
        name = str(type)

    args = get_args(type)
    if len(args) == 0:
        return name
    return f"{name}[{', '.join([type_args_string(arg) for arg in args])}]"


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
class UnknownFieldException(ValueError):
    field_name: str
    class_type: type

    def __str__(self):
        return f"Unknown field '{self.field_name}' for {type_args_string(self.class_type)}"


@dataclasses.dataclass
class NullNotAllowedException(ValueError):
    target_type: type

    def __str__(self):
        return f"None is not allowed for {type_args_string(self.target_type)}"


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


def __get_constructor_parameters(classType: type) -> list[inspect.Parameter]:
    try:
        signature = inspect.signature(classType)
    except (TypeError, ValueError):
        return []

    return [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    ]


def __get_type_hints_or_empty(target: Any) -> dict[str, type]:
    try:
        return get_type_hints(target)
    except (NameError, TypeError):
        return {}


def __construct_object(classType: type, parameters: list[inspect.Parameter], values: dict[str, Any]):
    args = []
    kwargs = {}

    for parameter in parameters:
        if parameter.name in values:
            value = values[parameter.name]
        elif parameter.default is inspect.Parameter.empty:
            # Preserve the existing missing-field behavior for now. F-05 will
            # introduce explicit required-field validation in a separate change.
            value = None
        else:
            # Omit optional parameters so the constructor can apply its own
            # default or dataclass default factory.
            continue

        if parameter.kind is inspect.Parameter.POSITIONAL_ONLY:
            args.append(value)
        else:
            kwargs[parameter.name] = value

    return classType(*args, **kwargs)


def __deserialize_simple_object(
    data: dict,
    classType: type,
    middleware: Optional[DeserializationMiddleware] = None,
    unknown_fields: UnknownFieldPolicy = "reject",
):
    middleware = __middleware_or_empty(middleware)
    attributes = get_attributes(classType)
    class_type_hints = __get_type_hints_or_empty(classType)
    init_type_hints = __get_type_hints_or_empty(classType.__init__)
    init_type_hints.pop("return", None)

    parameters = __get_constructor_parameters(classType)
    parameter_names = {parameter.name for parameter in parameters}

    field_types = dict(attributes)
    field_types.update(class_type_hints)
    field_types.update(init_type_hints)

    dataclass_non_init_fields = set()
    if dataclasses.is_dataclass(classType):
        dataclass_non_init_fields = {
            field.name for field in dataclasses.fields(classType) if not field.init
        }

    constructor_values = {}
    post_construction_values = {}

    for name, value in data.items():
        field_type = field_types.get(name)

        if name in dataclass_non_init_fields:
            # init=False fields belong to the constructor/__post_init__ lifecycle
            # and must not be overwritten from serialized input.
            continue

        is_known_field = name in parameter_names or name in field_types
        if not is_known_field:
            if unknown_fields == "reject":
                raise UnknownFieldException(name, classType)
            if unknown_fields == "ignore":
                continue

            # Explicit preserve mode retains the legacy behavior. Unknown values
            # have no declared target type, so they are attached unchanged after
            # normal construction.
            post_construction_values[name] = value
            continue

        try:
            deserialized_value = (
                __deserialize_inner(value, field_type, middleware, unknown_fields)
                if field_type
                else value
            )
        except Exception as e:
            raise DeserializeClassException(e, value, field_type, name)

        if name in parameter_names:
            constructor_values[name] = deserialized_value
        else:
            post_construction_values[name] = deserialized_value

    cls = __construct_object(classType, parameters, constructor_values)

    for name, value in post_construction_values.items():
        try:
            setattr(cls, name, value)
        except Exception as e:
            raise DeserializeClassException(e, value, field_types.get(name), name)

    return cls


def __deserialize_collection_items(
    values,
    collectionType: type,
    itemType: type,
    middleware: Optional[DeserializationMiddleware] = None,
    unknown_fields: UnknownFieldPolicy = "reject",
):
    middleware = __middleware_or_empty(middleware)
    deserialized = []
    for index in range(len(values)):
        value = values[index]
        try:
            deserialized.append(__deserialize_inner(value, itemType, middleware, unknown_fields))
        except Exception as e:
            raise DeserializeListException(e, value, collectionType, index)
    return deserialized


def __deserialize_list(
    values: list,
    listType: list[type],
    middleware: Optional[DeserializationMiddleware] = None,
    unknown_fields: UnknownFieldPolicy = "reject",
):
    typeArg = get_args(listType)[0] if get_args(listType) else Any
    return __deserialize_collection_items(values, listType, typeArg, middleware, unknown_fields)


def __deserialize_tuple(
    values: list,
    tupleType: tuple[type],
    middleware: Optional[DeserializationMiddleware] = None,
    unknown_fields: UnknownFieldPolicy = "reject",
):
    typeArgs = get_args(tupleType)
    if len(typeArgs) == 0:
        return tuple(values)
    if len(typeArgs) == 2 and typeArgs[1] is Ellipsis:
        return tuple(__deserialize_collection_items(values, tupleType, typeArgs[0], middleware, unknown_fields))

    if len(values) != len(typeArgs):
        raise BaseDeserializationException(Exception(f"Expected tuple of length {len(typeArgs)}, got {len(values)}"), values)

    deserialized = []
    for index, typeArg in enumerate(typeArgs):
        try:
            deserialized.append(__deserialize_inner(values[index], typeArg, middleware, unknown_fields))
        except Exception as e:
            raise DeserializeListException(e, values[index], tupleType, index)
    return tuple(deserialized)


def __deserialize_set(
    values: list,
    setType: set[type],
    middleware: Optional[DeserializationMiddleware] = None,
    unknown_fields: UnknownFieldPolicy = "reject",
):
    typeArg = get_args(setType)[0] if get_args(setType) else Any
    return set(__deserialize_collection_items(values, setType, typeArg, middleware, unknown_fields))


def __deserialize_frozenset(
    values: list,
    frozenSetType: frozenset[type],
    middleware: Optional[DeserializationMiddleware] = None,
    unknown_fields: UnknownFieldPolicy = "reject",
):
    typeArg = get_args(frozenSetType)[0] if get_args(frozenSetType) else Any
    return frozenset(__deserialize_collection_items(values, frozenSetType, typeArg, middleware, unknown_fields))


def __deserialize_dict(
    data: dict,
    keyType: type,
    valueType: type,
    middleware: Optional[DeserializationMiddleware] = None,
    unknown_fields: UnknownFieldPolicy = "reject",
):
    middleware = __middleware_or_empty(middleware)
    deserializedDict = {}
    for key, value in data.items():
        try:
            deserializedKey = __deserialize_inner(key, keyType, middleware, unknown_fields)
        except Exception as e:
            raise DeserializeDictKeyException(e, key, keyType, valueType)

        try:
            deserializedValue = __deserialize_inner(value, valueType, middleware, unknown_fields)
        except Exception as e:
            raise DeserializeDictValueException(e, value, keyType, valueType, key)

        deserializedDict[deserializedKey] = deserializedValue

    return deserializedDict


def __deserialize_union(
    value: Any,
    allowed_types: list[type],
    middleware: Optional[DeserializationMiddleware] = None,
    unknown_fields: UnknownFieldPolicy = "reject",
):
    middleware = __middleware_or_empty(middleware)
    value_type = type(value)
    for allowed_type in allowed_types:
        if allowed_type is Any or value_type is allowed_type:
            return value

    for allowed_type in allowed_types:
        try:
            return __deserialize_inner(value, allowed_type, middleware, unknown_fields)
        except Exception:
            pass

    raise BaseDeserializationException(Exception("Could not deserialize union"), value)


def __deserialize_literal(value: Any, literalType: type):
    allowed_values = get_args(literalType)
    for literal_value in allowed_values:
        if __literal_matches(value, literal_value):
            return value
    raise BaseDeserializationException(Exception(f"Expected one of {allowed_values}"), value)


def __deserialize_type_var(
    value: Any,
    typeVar: type,
    middleware: Optional[DeserializationMiddleware] = None,
    unknown_fields: UnknownFieldPolicy = "reject",
):
    constraints = getattr(typeVar, "__constraints__", ())
    if constraints:
        return __deserialize_union(value, constraints, middleware, unknown_fields)

    bound = getattr(typeVar, "__bound__", None)
    if bound is not None:
        return __deserialize_inner(value, bound, middleware, unknown_fields)

    return value


def deserialize(
    value: Any,
    classType: type,
    middleware: Optional[DeserializationMiddleware] = None,
    strict: bool = False,
    unknown_fields: Optional[UnknownFieldPolicy] = None,
):
    resolved_unknown_fields = __resolve_unknown_field_policy(strict, unknown_fields)

    try:
        return __deserialize_inner(
            value,
            classType,
            __middleware_or_empty(middleware),
            resolved_unknown_fields,
        )
    except Exception as e:
        raise DeserializeClassException(e, value, classType, None)


def __deserialize_inner(
    value: Any,
    classType: type,
    middleware: Optional[DeserializationMiddleware] = None,
    unknown_fields: UnknownFieldPolicy = "reject",
):
    middleware = __middleware_or_empty(middleware)

    def deserialize_primitive(classType: type, value: Any):
        try:
            return classType(value)
        except Exception as e:
            raise BaseDeserializationException(e, value)

    if classType is Any:
        return value
    if __is_literal(classType):
        return __deserialize_literal(value, classType)
    if value is None:
        if __allows_none(classType):
            return None
        raise NullNotAllowedException(classType)
    if __is_type_var(classType):
        return __deserialize_type_var(value, classType, middleware, unknown_fields)
    if (deserializer := middleware.get(classType, None)) is not None:
        return deserializer(value, middleware)
    if is_primitive(classType):
        return deserialize_primitive(classType, value)
    if is_enum(classType):
        return deserialize_primitive(classType, value)
    if is_optional(classType):
        realType = [arg for arg in get_args(classType) if arg is not type(None)][0]
        return __deserialize_inner(value, realType, middleware, unknown_fields)

    originType = get_origin(classType)
    typeArgs = get_args(classType)
    if originType is list:
        return __deserialize_list(value, classType, middleware, unknown_fields)
    if originType is tuple:
        return __deserialize_tuple(value, classType, middleware, unknown_fields)
    if originType is set:
        return __deserialize_set(value, classType, middleware, unknown_fields)
    if originType is frozenset:
        return __deserialize_frozenset(value, classType, middleware, unknown_fields)
    if originType is dict:
        keyType = typeArgs[0] if len(typeArgs) > 0 else Any
        valueType = typeArgs[1] if len(typeArgs) > 1 else Any
        return __deserialize_dict(value, keyType, valueType, middleware, unknown_fields)
    if is_union(classType):
        return __deserialize_union(value, get_args(classType), middleware, unknown_fields)

    return __deserialize_simple_object(value, classType, middleware, unknown_fields)

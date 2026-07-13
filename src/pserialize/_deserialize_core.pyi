from typing import Any, Literal, Optional

from .middleware_context import DeserializationMiddleware


UnknownFieldPolicy = Literal["reject", "ignore", "preserve"]


class DeserializationMismatch(ValueError): ...


class BaseDeserializationException(DeserializationMismatch):
    error: Exception
    value: Any


class UnknownFieldException(DeserializationMismatch):
    field_name: str
    class_type: type


class NullNotAllowedException(DeserializationMismatch):
    target_type: type


class MissingRequiredFieldException(DeserializationMismatch):
    field_name: str
    class_type: type


class TypeMismatchException(BaseDeserializationException):
    expected_type: type
    actual_type: type
    reason: Optional[str]


class UnionDeserializationException(BaseDeserializationException):
    allowed_types: tuple[type, ...]
    branch_errors: tuple[tuple[type, DeserializationMismatch], ...]


class DeserializeDictKeyException(BaseDeserializationException):
    keyType: type
    valueType: type


class DeserializeDictValueException(BaseDeserializationException):
    keyType: type
    valueType: type
    key: Any


class DeserializeListException(BaseDeserializationException):
    itemType: type
    index: int


class DeserializeClassException(BaseDeserializationException):
    field_type: type
    field_name: str


def type_args_string(type: type) -> str: ...


def deserialize(
    value: Any,
    classType: type,
    middleware: Optional[DeserializationMiddleware] = ...,
    strict: bool = ...,
    unknown_fields: Optional[UnknownFieldPolicy] = ...,
    coerce: bool = ...,
) -> Any: ...

"""Compatibility module for the public deserialization API."""

from .deserialize_impl import (
    BaseDeserializationException,
    DeserializationMismatch,
    DeserializeClassException,
    DeserializeDictKeyException,
    DeserializeDictValueException,
    DeserializeListException,
    MissingRequiredFieldException,
    NullNotAllowedException,
    TypeMismatchException,
    UnionDeserializationException,
    UnknownFieldException,
    UnknownFieldPolicy,
    deserialize,
    type_args_string,
)

__all__ = [
    "BaseDeserializationException",
    "DeserializationMismatch",
    "DeserializeClassException",
    "DeserializeDictKeyException",
    "DeserializeDictValueException",
    "DeserializeListException",
    "MissingRequiredFieldException",
    "NullNotAllowedException",
    "TypeMismatchException",
    "UnionDeserializationException",
    "UnknownFieldException",
    "UnknownFieldPolicy",
    "deserialize",
    "type_args_string",
]

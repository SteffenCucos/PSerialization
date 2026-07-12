"""Public deserialization implementation facade.

The deserialization engine lives in ``_deserialize_core``. This facade defines
and enforces the public middleware contract while preserving the engine's
existing exception types and recursive behavior.
"""

from typing import Any, Optional

from . import _deserialize_core as _core
from .middleware_context import (
    DeserializationContext,
    DeserializationMiddleware,
    DeserializerMiddleware,
)


BaseDeserializationException = _core.BaseDeserializationException
DeserializationMismatch = _core.DeserializationMismatch
DeserializeClassException = _core.DeserializeClassException
DeserializeDictKeyException = _core.DeserializeDictKeyException
DeserializeDictValueException = _core.DeserializeDictValueException
DeserializeListException = _core.DeserializeListException
MissingRequiredFieldException = _core.MissingRequiredFieldException
NullNotAllowedException = _core.NullNotAllowedException
TypeMismatchException = _core.TypeMismatchException
UnionDeserializationException = _core.UnionDeserializationException
UnknownFieldException = _core.UnknownFieldException
UnknownFieldPolicy = _core.UnknownFieldPolicy
type_args_string = _core.type_args_string


def deserialize(
    value: Any,
    classType: type,
    middleware: Optional[DeserializationMiddleware] = None,
    strict: bool = False,
    unknown_fields: Optional[UnknownFieldPolicy] = None,
    coerce: bool = False,
):
    """Deserialize a value using optional type-specific middleware.

    Middleware callables receive ``(value, context)``. The context is a
    read-only mapping of the registered middleware and exposes
    ``context.deserialize(value, target_type)`` for recursive deserialization
    with the same unknown-field and primitive-coercion policies.
    """
    if type(coerce) is not bool:
        raise TypeError("coerce must be a bool")

    resolve_policy = getattr(_core, "__resolve_unknown_field_policy")
    deserialize_inner = getattr(_core, "__deserialize_inner")
    resolved_unknown_fields = resolve_policy(strict, unknown_fields)

    context = DeserializationContext(
        middleware,
        unknown_fields=resolved_unknown_fields,
        coerce=coerce,
    )
    context._bind(
        lambda nested_value, target_type: deserialize_inner(
            nested_value,
            target_type,
            context,
            resolved_unknown_fields,
        )
    )

    return _core.deserialize(
        value,
        classType,
        context,
        strict,
        unknown_fields,
        coerce,
    )


__all__ = [
    "BaseDeserializationException",
    "DeserializationContext",
    "DeserializationMiddleware",
    "DeserializerMiddleware",
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

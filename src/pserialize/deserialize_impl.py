"""Public deserialization implementation facade.

The deserialization engine lives in ``_deserialize_core``. This facade defines
and enforces the public middleware contract while preserving the engine's
existing exception types and recursive behavior.
"""

from collections.abc import Mapping, Sequence
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


def _redacted_base_exception_repr(error: BaseDeserializationException) -> str:
    """Format a deserialization failure without rendering its raw input value."""
    if isinstance(error.error, BaseDeserializationException):
        return " -> " + str(error.error)
    return f"Deserialization failed ({type(error.error).__name__})"


def _redacted_type_mismatch_repr(error: TypeMismatchException) -> str:
    """Describe the type mismatch using types only, never the rejected value."""
    return (
        f"Expected {type_args_string(error.expected_type)}, "
        f"got {type_args_string(error.actual_type)}"
    )


def _redacted_union_exception_repr(
    error: UnionDeserializationException,
) -> str:
    """Retain branch diagnostics while relying on each branch's safe formatter."""
    branches = "; ".join(
        f"{type_args_string(branch_type)}: {branch_error}"
        for branch_type, branch_error in error.branch_errors
    )
    return f"No union branch matched ({branches})"


# Exception classes are defined in the private core, but their public rendering
# contract belongs to this facade. Keep raw values available as structured
# ``.value`` fields for callers that explicitly inspect them while preventing
# accidental disclosure through logging, ``str(error)``, or ``repr(error)``.
BaseDeserializationException.__repr__ = _redacted_base_exception_repr
TypeMismatchException.__repr__ = _redacted_type_mismatch_repr
UnionDeserializationException.__repr__ = _redacted_union_exception_repr


_TEXT_LIKE_SEQUENCE_TYPES = (str, bytes, bytearray, memoryview)


def _require_mapping(value: Any, target_type: type) -> Mapping:
    if not isinstance(value, Mapping):
        raise TypeMismatchException(
            value,
            target_type,
            type(value),
            "expected a mapping-shaped input",
        )
    return value


def _require_sequence(value: Any, target_type: type) -> Sequence:
    if not isinstance(value, Sequence) or isinstance(
        value,
        _TEXT_LIKE_SEQUENCE_TYPES,
    ):
        raise TypeMismatchException(
            value,
            target_type,
            type(value),
            "expected a non-text sequence input",
        )
    return value


def _deserialize_raw_list(value: Any, context: DeserializationContext) -> list:
    sequence = _require_sequence(value, list)
    return [context.deserialize(item, Any) for item in sequence]


def _deserialize_raw_tuple(value: Any, context: DeserializationContext) -> tuple:
    sequence = _require_sequence(value, tuple)
    return tuple(context.deserialize(item, Any) for item in sequence)


def _deserialize_raw_set(value: Any, context: DeserializationContext) -> set:
    sequence = _require_sequence(value, set)
    return {context.deserialize(item, Any) for item in sequence}


def _deserialize_raw_frozenset(
    value: Any,
    context: DeserializationContext,
) -> frozenset:
    sequence = _require_sequence(value, frozenset)
    return frozenset(context.deserialize(item, Any) for item in sequence)


def _deserialize_raw_dict(value: Any, context: DeserializationContext) -> dict:
    mapping = _require_mapping(value, dict)
    return {
        context.deserialize(key, Any): context.deserialize(item, Any)
        for key, item in mapping.items()
    }


_RAW_COLLECTION_DESERIALIZERS: dict[type, DeserializerMiddleware] = {
    list: _deserialize_raw_list,
    tuple: _deserialize_raw_tuple,
    set: _deserialize_raw_set,
    frozenset: _deserialize_raw_frozenset,
    dict: _deserialize_raw_dict,
}


def _build_contexts(
    middleware: Optional[DeserializationMiddleware],
    *,
    unknown_fields: UnknownFieldPolicy,
    coerce: bool,
) -> tuple[DeserializationContext, DeserializationContext]:
    """Build public and engine contexts with hidden raw-collection fallbacks."""
    registered = dict(middleware) if middleware is not None else {}
    public_context = DeserializationContext(
        registered,
        unknown_fields=unknown_fields,
        coerce=coerce,
    )

    effective = dict(_RAW_COLLECTION_DESERIALIZERS)
    effective.update(registered)

    # The engine receives wrappers so every middleware callable, including the
    # internal collection fallbacks, sees the public context rather than the
    # effective registry containing implementation details.
    engine_middleware: dict[type, DeserializerMiddleware] = {}
    for target_type, deserializer in effective.items():
        engine_middleware[target_type] = (
            lambda value, _engine_context, handler=deserializer: handler(
                value,
                public_context,
            )
        )

    engine_context = DeserializationContext(
        engine_middleware,
        unknown_fields=unknown_fields,
        coerce=coerce,
    )
    return public_context, engine_context


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

    public_context, engine_context = _build_contexts(
        middleware,
        unknown_fields=resolved_unknown_fields,
        coerce=coerce,
    )

    recursive_deserialize = lambda nested_value, target_type: deserialize_inner(
        nested_value,
        target_type,
        engine_context,
        resolved_unknown_fields,
    )
    public_context._bind(recursive_deserialize)
    engine_context._bind(recursive_deserialize)

    return _core.deserialize(
        value,
        classType,
        engine_context,
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

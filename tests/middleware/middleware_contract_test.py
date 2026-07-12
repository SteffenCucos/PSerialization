from dataclasses import dataclass
from datetime import datetime

import pytest

from src.pserialize import (
    DeserializationContext,
    Deserializer,
    SerializationContext,
    Serializer,
    deserialize,
    serialize,
)
from src.pserialize.serialize import SerializeCycleException


def test_serialization_middleware_receives_context_and_registry():
    observed = {}

    def serialize_datetime(value: datetime, context: SerializationContext):
        observed["context"] = context
        observed["registered"] = context.get(datetime)
        return value.isoformat()

    middleware = {datetime: serialize_datetime}
    result = serialize(datetime(2026, 7, 12, 10, 30), middleware)

    assert result == "2026-07-12T10:30:00"
    assert isinstance(observed["context"], SerializationContext)
    assert observed["registered"] is serialize_datetime


def test_deserialization_middleware_receives_context_and_registry():
    observed = {}

    def deserialize_datetime(value: str, context: DeserializationContext):
        observed["context"] = context
        observed["registered"] = context.get(datetime)
        return datetime.fromisoformat(value)

    middleware = {datetime: deserialize_datetime}
    result = deserialize("2026-07-12T10:30:00", datetime, middleware)

    assert result == datetime(2026, 7, 12, 10, 30)
    assert isinstance(observed["context"], DeserializationContext)
    assert observed["registered"] is deserialize_datetime


def test_serialization_context_preserves_recursive_middleware_application():
    @dataclass
    class Envelope:
        value: datetime

    def serialize_envelope(value: Envelope, context: SerializationContext):
        return {"value": context.serialize(value.value)}

    def serialize_datetime(value: datetime, context: SerializationContext):
        return value.isoformat()

    result = Serializer(
        middleware={
            Envelope: serialize_envelope,
            datetime: serialize_datetime,
        }
    ).serialize(Envelope(datetime(2026, 7, 12, 10, 30)))

    assert result == {"value": "2026-07-12T10:30:00"}


def test_deserialization_context_preserves_recursive_middleware_application():
    @dataclass
    class Envelope:
        value: datetime

    def deserialize_envelope(value: dict, context: DeserializationContext):
        return Envelope(context.deserialize(value["value"], datetime))

    def deserialize_datetime(value: str, context: DeserializationContext):
        return datetime.fromisoformat(value)

    result = Deserializer(
        middleware={
            Envelope: deserialize_envelope,
            datetime: deserialize_datetime,
        }
    ).deserialize({"value": "2026-07-12T10:30:00"}, Envelope)

    assert result == Envelope(datetime(2026, 7, 12, 10, 30))


def test_deserialization_context_exposes_active_configuration():
    class WrappedInt:
        def __init__(self, value: int):
            self.value = value

    def deserialize_wrapped(value: str, context: DeserializationContext):
        assert context.unknown_fields == "ignore"
        assert context.coerce is True
        return WrappedInt(context.deserialize(value, int))

    result = deserialize(
        "4",
        WrappedInt,
        middleware={WrappedInt: deserialize_wrapped},
        unknown_fields="ignore",
        coerce=True,
    )

    assert result.value == 4


def test_serialization_context_preserves_cycle_detection_state():
    class Node:
        pass

    node = Node()

    def serialize_node(value: Node, context: SerializationContext):
        return context.serialize(value)

    with pytest.raises(SerializeCycleException):
        serialize(node, middleware={Node: serialize_node})


def test_runtime_consistently_requires_two_argument_serializer_middleware():
    def one_argument(value):
        return str(value)

    with pytest.raises(TypeError):
        serialize(datetime(2026, 7, 12), middleware={datetime: one_argument})


def test_runtime_consistently_requires_two_argument_deserializer_middleware():
    def one_argument(value):
        return value

    with pytest.raises(TypeError):
        deserialize("2026-07-12", datetime, middleware={datetime: one_argument})

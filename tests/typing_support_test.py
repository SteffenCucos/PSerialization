from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Tuple, TypeVar

from src.pserialize import Deserializer, Serializer, deserialize


ConstrainedScalar = TypeVar("ConstrainedScalar", int, str)
BoundInt = TypeVar("BoundInt", bound=int)


def test_legacy_typing_generics_deserialize():
    @dataclass
    class Payload:
        items: List[int]
        lookup: Dict[str, Tuple[int, str]]

    value = deserialize(
        {
            "items": ["1", 2, 3.0],
            "lookup": {
                "first": [1, "one"],
                "second": ["2", "two"],
            },
        },
        Payload,
    )

    assert value == Payload(
        items=[1, 2, 3],
        lookup={
            "first": (1, "one"),
            "second": (2, "two"),
        },
    )


def test_any_annotation_returns_value_unchanged():
    @dataclass
    class Envelope:
        payload: Any

    payload = {"nested": [1, "two", {"three": 3}]}

    value = deserialize({"payload": payload}, Envelope)

    assert value == Envelope(payload)
    assert value.payload is payload


def test_literal_accepts_allowed_values():
    @dataclass
    class Config:
        mode: Literal["fast", "safe"]
        retries: Literal[3]

    value = deserialize({"mode": "fast", "retries": 3}, Config)

    assert value == Config(mode="fast", retries=3)


def test_literal_rejects_disallowed_values():
    @dataclass
    class Config:
        mode: Literal["fast", "safe"]

    error = None

    try:
        deserialize({"mode": "slow"}, Config)
    except Exception as e:
        error = e

    assert error is not None
    assert "Expected one of" in str(error)


def test_literal_requires_exact_value_type():
    @dataclass
    class Config:
        enabled: Literal[1]

    error = None

    try:
        deserialize({"enabled": True}, Config)
    except Exception as e:
        error = e

    assert error is not None
    assert "Expected one of" in str(error)


def test_constrained_typevar_prefers_existing_value_type():
    @dataclass
    class Box:
        value: ConstrainedScalar

    assert deserialize({"value": "4"}, Box) == Box("4")
    assert deserialize({"value": 4.0}, Box) == Box(4)


def test_bound_typevar_deserializes_to_bound_type():
    @dataclass
    class User:
        id: BoundInt

    assert deserialize({"id": "42"}, User) == User(42)


def test_default_middlewares_are_not_shared():
    serializer_a = Serializer()
    serializer_b = Serializer()
    deserializer_a = Deserializer()
    deserializer_b = Deserializer()

    serializer_a.middleware[int] = lambda value, _: value
    deserializer_a.middleware[int] = lambda value, _: value

    assert int not in serializer_b.middleware
    assert int not in deserializer_b.middleware

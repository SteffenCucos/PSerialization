from dataclasses import dataclass, field

import pytest

from src.pserialize import deserialize


def test_deserialize_calls_constructor():
    calls = []

    class Model:
        value: int

        def __init__(self, value: int):
            calls.append(value)
            self.value = value

    result = deserialize({"value": "3"}, Model)

    assert result.value == 3
    assert calls == [3]


def test_constructor_validation_is_enforced():
    class Account:
        balance: int

        def __init__(self, balance: int):
            if balance < 0:
                raise ValueError("balance cannot be negative")
            self.balance = balance

    with pytest.raises(Exception, match="balance cannot be negative"):
        deserialize({"balance": -1}, Account)


def test_dataclass_post_init_runs():
    @dataclass
    class Model:
        value: int
        doubled: int = field(init=False)

        def __post_init__(self):
            self.doubled = self.value * 2

    result = deserialize({"value": "4", "doubled": 999}, Model)

    assert result == Model(4)
    assert result.doubled == 8


def test_frozen_dataclass_uses_normal_construction():
    @dataclass(frozen=True)
    class FrozenModel:
        value: int

    result = deserialize({"value": "4"}, FrozenModel)

    assert result == FrozenModel(4)


def test_slots_class_uses_normal_construction():
    class SlotsModel:
        __slots__ = ("value", "constructed")

        def __init__(self, value: int):
            self.value = value
            self.constructed = True

    result = deserialize({"value": "4"}, SlotsModel)

    assert result.value == 4
    assert result.constructed is True
    assert not hasattr(result, "__dict__")


def test_constructor_default_is_preserved_when_field_is_missing():
    @dataclass
    class Model:
        value: int
        label: str = "default"

    result = deserialize({"value": 1}, Model)

    assert result == Model(1, "default")


def test_missing_required_field_preserves_legacy_none_behavior_for_now():
    @dataclass
    class Model:
        value: int
        name: str

    result = deserialize({"value": 1}, Model)

    assert result == Model(1, None)

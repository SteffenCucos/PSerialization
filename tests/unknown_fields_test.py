from dataclasses import dataclass

import pytest

from src.pserialize import Deserializer, UnknownFieldException, deserialize
from src.pserialize.deserialize import DeserializeClassException


def test_unknown_fields_are_rejected_by_default():
    @dataclass
    class User:
        name: str

    with pytest.raises(DeserializeClassException) as captured:
        deserialize({"name": "Alice", "is_admin": True}, User)

    assert isinstance(captured.value.error, UnknownFieldException)
    assert captured.value.error.field_name == "is_admin"
    assert captured.value.error.class_type is User
    assert "Unknown field 'is_admin' for User" in str(captured.value)


def test_unknown_fields_can_be_explicitly_ignored():
    @dataclass
    class User:
        name: str

    user = deserialize(
        {"name": "Alice", "is_admin": True},
        User,
        unknown_fields="ignore",
    )

    assert user == User("Alice")
    assert not hasattr(user, "is_admin")


def test_unknown_fields_can_be_explicitly_preserved():
    @dataclass
    class User:
        name: str

    user = deserialize(
        {"name": "Alice", "is_admin": True},
        User,
        unknown_fields="preserve",
    )

    assert user == User("Alice")
    assert user.is_admin is True


def test_strict_true_remains_compatible_with_ignore_behavior():
    @dataclass
    class User:
        name: str

    user = deserialize(
        {"name": "Alice", "extra": "ignored"},
        User,
        strict=True,
    )

    assert user == User("Alice")
    assert not hasattr(user, "extra")


def test_explicit_policy_takes_precedence_over_legacy_strict_flag():
    @dataclass
    class User:
        name: str

    user = deserialize(
        {"name": "Alice", "extra": "preserved"},
        User,
        strict=True,
        unknown_fields="preserve",
    )

    assert user.extra == "preserved"


def test_unknown_field_policy_propagates_into_nested_objects():
    @dataclass
    class Child:
        name: str

    @dataclass
    class Parent:
        child: Child

    payload = {
        "child": {
            "name": "Alice",
            "is_admin": True,
        }
    }

    with pytest.raises(DeserializeClassException) as captured:
        deserialize(payload, Parent)

    assert "child:Child" in str(captured.value)
    assert "Unknown field 'is_admin' for Child" in str(captured.value)

    ignored = deserialize(payload, Parent, unknown_fields="ignore")
    assert ignored == Parent(Child("Alice"))
    assert not hasattr(ignored.child, "is_admin")


def test_unknown_field_policy_propagates_through_collections():
    @dataclass
    class User:
        name: str

    payload = [{"name": "Alice", "extra": 1}]

    with pytest.raises(DeserializeClassException, match="Unknown field 'extra' for User"):
        deserialize(payload, list[User])

    assert deserialize(payload, list[User], unknown_fields="ignore") == [User("Alice")]


def test_deserializer_convenience_class_accepts_unknown_field_policy():
    @dataclass
    class User:
        name: str

    deserializer = Deserializer()
    user = deserializer.deserialize(
        {"name": "Alice", "extra": 1},
        User,
        unknown_fields="ignore",
    )

    assert user == User("Alice")
    assert not hasattr(user, "extra")


def test_invalid_unknown_field_policy_is_rejected_before_deserialization():
    @dataclass
    class User:
        name: str

    with pytest.raises(ValueError, match="unknown_fields must be one of"):
        deserialize(
            {"name": "Alice"},
            User,
            unknown_fields="drop",  # type: ignore[arg-type]
        )

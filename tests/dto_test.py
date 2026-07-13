from dataclasses import dataclass
from datetime import datetime

from src.pserialize.serialize import serialize_into


def test_serialize_into_returns_primitive_output_shaped_by_target():
    @dataclass
    class User:
        id: int
        name: str
        email: str
        password: str  # Sensitive field

    @dataclass
    class UserDTO:
        id: int
        name: str
        email: str

    user = User(1, "Andy", "andy@gmail.com", "super_secret")

    serialized = serialize_into(user, UserDTO)

    assert serialized == {
        "id": 1,
        "name": "Andy",
        "email": "andy@gmail.com",
    }
    assert type(serialized) is dict


def test_serialize_into_preserves_middleware_for_final_serialization():
    @dataclass
    class Source:
        created_at: datetime

    @dataclass
    class Target:
        created_at: datetime

    created_at = datetime(2026, 7, 12, 18, 30)
    serialization_calls = []
    deserialization_calls = []

    def serialize_datetime(value, _context):
        serialization_calls.append(value)
        return value.isoformat()

    def deserialize_datetime(value, _context):
        deserialization_calls.append(value)
        return datetime.fromisoformat(value)

    result = serialize_into(
        Source(created_at),
        Target,
        s_middleware={datetime: serialize_datetime},
        d_middleware={datetime: deserialize_datetime},
    )

    assert result == {"created_at": "2026-07-12T18:30:00"}
    assert serialization_calls == [created_at, created_at]
    assert deserialization_calls == ["2026-07-12T18:30:00"]

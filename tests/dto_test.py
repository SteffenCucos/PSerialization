

from dataclasses import dataclass

from src.pserialize.serialize import default_serializer as serializer

def test_serialize_into():
    @dataclass
    class User:
        id: int
        name: str
        email: str
        password: str # Sensitive field

    @dataclass
    class UserDTO:
        id: int
        name: str
        email: str

    user = User(1, "Andy", "andy@gmail.com", "super_secret")

    serialized = serializer.serialize_into(user, UserDTO)

    # Make sure password didn't get serialized
    assert serialized == {
        "id": 1,
        "name": "Andy",
        "email": "andy@gmail.com"
    }
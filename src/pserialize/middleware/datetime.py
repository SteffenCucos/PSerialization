

from src.pserialize.deserialize import Deserializer
from src.pserialize.serialize import Serializer

from datetime import datetime


class _datetime:
    @staticmethod
    def deserializer(deserializer: Deserializer, value: str) -> datetime:
        return datetime.fromisoformat(value)

    @staticmethod
    def serializer(serializer: Serializer, obj: datetime) -> str:
        return obj.isoformat()

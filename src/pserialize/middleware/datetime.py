

from datetime import datetime

class _datetime:
    @staticmethod
    def deserializer(value: str) -> datetime:
        return datetime.fromisoformat(value)

    @staticmethod
    def serializer(obj: datetime) -> str:
        return obj.isoformat()

    # Add concept of dto to serialize into, to give the ability to avoid serializing certain fields
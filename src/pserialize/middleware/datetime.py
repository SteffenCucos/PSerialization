from datetime import datetime

from ..middleware_context import DeserializationContext, SerializationContext


class _datetime:
    @staticmethod
    def deserializer(
        value: str,
        context: DeserializationContext,
    ) -> datetime:
        return datetime.fromisoformat(value)

    @staticmethod
    def serializer(
        value: datetime,
        context: SerializationContext,
    ) -> str:
        return value.isoformat()

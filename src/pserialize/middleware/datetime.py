from typing import Callable

from datetime import datetime


class _datetime:
    @staticmethod
    def deserializer(value: str, middleware: dict[type, Callable[[object], type]] = {}) -> datetime:
        return datetime.fromisoformat(value)

    @staticmethod
    def serializer(obj: datetime, middleware: dict[type, Callable[[object], type]] = {}) -> str:
        return obj.isoformat()

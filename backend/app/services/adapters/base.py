from abc import ABC, abstractmethod
from typing import Any


class SourceAdapter(ABC):
    name: str

    @abstractmethod
    async def fetch_updates(self, condition_name: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw_item: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def dedupe_key(self, normalized_item: dict[str, Any]) -> str:
        raise NotImplementedError

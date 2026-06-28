from abc import ABC, abstractmethod
from typing import Any


class ContextSource(ABC):
    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        """Return list of service config dicts."""
        ...

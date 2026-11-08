from abc import ABC, abstractmethod
from typing import Any


class LoadableModel(ABC):
    """Common interface every model wrapper implements, so ModelManager
    can treat all five models uniformly."""

    #: True for models that stay loaded permanently (M3, M4)
    always_resident: bool = False

    def __init__(self):
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @abstractmethod
    def load(self) -> None:
        """Load weights into memory. Must be idempotent — calling load()
        on an already-loaded model should be a cheap no-op."""
        ...

    @abstractmethod
    def infer(self, *args, **kwargs) -> Any:
        """Run one inference call. Assumes load() has already happened —
        ModelManager guarantees this, this method doesn't need to check."""
        ...

    @abstractmethod
    def unload(self) -> None:
        """Free the memory. Must be safe to call even if never loaded."""
        ...

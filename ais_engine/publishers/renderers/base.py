"""Reconstructed renderer contract; original file was not recoverable."""
from abc import ABC, abstractmethod

class BaseRenderer(ABC):
    @abstractmethod
    def render(self, signals, subscriber) -> list[str]:
        raise NotImplementedError

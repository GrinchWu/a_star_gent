"""Agent基类"""
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self, **kwargs) -> dict:
        pass

    def log(self, msg: str):
        print(f"[{self.name}] {msg}")

from abc import ABC, abstractmethod
from typing import List, Optional

class Node(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self) -> bool:
        """Returns True for Success, False for Failure"""
        pass

class Leaf(Node):
    """Base class for all actions and conditions"""
    @abstractmethod
    def run(self) -> bool:
        pass

class Composite(Node):
    """Base class for nodes with children"""
    def __init__(self, name: str, children: List[Node]):
        super().__init__(name)
        self.children = children

class Selector(Composite):
    """Returns success if any child succeeds (OR)"""
    def run(self) -> bool:
        for child in self.children:
            if child.run():
                return True
        return False

class Sequence(Composite):
    """Returns success only if all children succeed (AND)"""
    def run(self) -> bool:
        for child in self.children:
            if not child.run():
                return False
        return True

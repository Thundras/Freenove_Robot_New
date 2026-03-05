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

class Parallel(Composite):
    """Runs all children. Succeeds if a required number of children succeed."""
    def __init__(self, name: str, children: List[Node], success_threshold: Optional[int] = None):
        super().__init__(name, children)
        self.success_threshold = success_threshold or len(children)

    def run(self) -> bool:
        successes = 0
        for child in self.children:
            if child.run():
                successes += 1
        return successes >= self.success_threshold

class Decorator(Node):
    """Base class for nodes that modify a single child's behavior"""
    def __init__(self, name: str, child: Node):
        super().__init__(name)
        self.child = child

class Inverter(Decorator):
    """Inverts the result of the child node"""
    def run(self) -> bool:
        return not self.child.run()

class Condition(Leaf):
    """A leaf node that just checks a function/lambda/state"""
    def __init__(self, name: str, check_fn):
        super().__init__(name)
        self.check_fn = check_fn

    def run(self) -> bool:
        return self.check_fn()

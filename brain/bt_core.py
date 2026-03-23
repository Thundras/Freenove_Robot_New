from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import random
import math
import logging

logger = logging.getLogger(__name__)


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

    def __init__(
        self, name: str, children: List[Node], success_threshold: Optional[int] = None
    ):
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


class WeightedChoice:
    def __init__(self, node: Node, weight: float, condition: Optional[str] = None):
        self.node = node
        self.weight = weight
        self.condition = condition


class WeightedSelector(Composite):
    """Picks ONE child based on weights. Useful for 'deciding' what to do."""

    def __init__(
        self, name: str, choices: List[WeightedChoice], context: Dict[str, Any]
    ):
        super().__init__(name, [c.node for c in choices])
        self.choices = choices
        self.context = context

    def run(self) -> bool:
        valid_choices = []
        for choice in self.choices:
            # Simple condition check
            if choice.condition:
                try:
                    # In a real impl, we'd use a safe evaluator. For now, simple context check.
                    if not self._evaluate_condition(choice.condition):
                        continue
                except:
                    continue
            valid_choices.append(choice)

        if not valid_choices:
            return False

        total_weight = sum(c.weight for c in valid_choices)
        pick = random.uniform(0, total_weight)
        current = 0
        for choice in valid_choices:
            current += choice.weight
            if pick <= current:
                return choice.node.run()
        return False

    def _evaluate_condition(self, condition: str) -> bool:
        # Placeholder for the DNA Expression Engine
        # We'll implement a proper safe eval in Phase 1
        safe_dict = {
            "mood": self.context.get("mood"),
            "energy": self.context.get("energy", 1.0),
            "time": self.context.get("time", 0.0),
            "sin": math.sin,
            "cos": math.cos,
            "mapping": self.context.get("mapping"),
            "last_object": self.context.get("last_object_detection"),
            "last_face": self.context.get("last_face"),
            "mode": self.context.get("system_mode"),
            "system_mode": self.context.get("system_mode"),
            "config": self.context["sensors"]["intelligence"].config
            if "sensors" in self.context and "intelligence" in self.context["sensors"]
            else {},
        }
        try:
            return eval(condition, {"__builtins__": None}, safe_dict)
        except Exception as e:
            logger.error(f"Condition Eval Error: {condition} -> {e}")
            return False


class ConditionDecorator(Node):
    """Wraps a node with a condition check"""

    def __init__(self, name: str, child: Node, condition: str, context: Dict[str, Any]):
        super().__init__(name)
        self.child = child
        self.condition = condition
        self.context = context

    def run(self) -> bool:
        # Re-use the same evaluation logic
        safe_dict = {
            "mood": self.context.get("mood"),
            "energy": self.context.get("energy", 1.0),
            "time": self.context.get("time", 0.0),
            "sin": math.sin,
            "cos": math.cos,
            "mapping": self.context.get("mapping"),
            "last_object": self.context.get("last_object_detection"),
            "last_face": self.context.get("last_face"),
            "mode": self.context.get("system_mode"),
            "system_mode": self.context.get("system_mode"),
            "config": self.context["sensors"]["intelligence"].config
            if "sensors" in self.context and "intelligence" in self.context["sensors"]
            else {},
        }
        try:
            if eval(self.condition, {"__builtins__": None}, safe_dict):
                return self.child.run()
        except:
            pass
        return False


class ParameterLeaf(Leaf):
    """A leaf node that evaluates parameters every tick from the context"""

    def __init__(
        self,
        name: str,
        context: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name)
        self.context = context
        self.raw_params = params
        self.current_params = {}

    def _eval_params(self):
        """Resolves dynamic strings to values and handles feature inhibition"""
        if self.raw_params is None:
            self.current_params = {}
            return
        for k, v in self.raw_params.items():
            if isinstance(v, str) and ("mood." in v or "energy" in v or "sin(" in v):
                try:
                    # Context includes: mood, energy, time, mapping, last_object, etc.
                    safe_dict = {
                        "mood": self.context.get("mood"),
                        "energy": self.context.get("energy", 1.0),
                        "time": self.context.get("time", 0.0),
                        "sin": math.sin,
                        "cos": math.cos,
                        "mapping": self.context.get("mapping"),
                        "mode": self.context.get("system_mode"),
                        "system_mode": self.context.get("system_mode"),
                    }
                    self.current_params[k] = eval(v, {"__builtins__": None}, safe_dict)
                except Exception as e:
                    logger.error(f"Error evaluating param {k}={v}: {e}")
                    # If it's a numeric-sounding key, default to a safe value instead of the raw string
                    if k in [
                        "speed",
                        "turn",
                        "pitch",
                        "roll",
                        "yaw",
                        "x",
                        "y",
                        "z",
                        "speed_mod",
                    ]:
                        self.current_params[k] = self.current_params.get(k, 0.0)
                    else:
                        self.current_params[k] = v
            else:
                self.current_params[k] = v

        # Handle Sensor Inhibition
        if "disable_features" in self.current_params:
            inhibited = self.current_params["disable_features"]
            if isinstance(inhibited, list):
                if "inhibited_features" not in self.context:
                    self.context["inhibited_features"] = set()
                for feature in inhibited:
                    self.context["inhibited_features"].add(feature)

    @abstractmethod
    def run(self) -> bool:
        self._eval_params()
        pass


class AdditiveLayer(ParameterLeaf):
    """Special node that ADDS offsets to the gait engine instead of setting them"""

    def run(self) -> bool:
        self._eval_params()
        if "gait" in self.context:
            self.context["gait"].add_additive_layer(self.name, self.current_params)
            return True
        return False

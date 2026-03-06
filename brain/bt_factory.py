import yaml
import logging
from typing import Dict, Any, List
from .bt_core import Selector, Sequence, Parallel, WeightedSelector, WeightedChoice, AdditiveLayer, ConditionDecorator
from .behaviors import (
    AvoidObstacles, SmartExplore, ReactToPerson, FollowPerson, Idle, 
    HandleGesture, AlarmPulse, SecurityMonitor, DogSocialInteraction, 
    PlayWithBall, AmbientLook, ReactToFace, ExpressMood, AutoLevel,
    SniffAnimation
)

logger = logging.getLogger(__name__)

# Action Nodes for simple parameter tweaks
from .bt_core import ParameterLeaf

class SetSpeed(ParameterLeaf):
    def run(self) -> bool:
        self._eval_params()
        if "gait" in self.context:
            speed = self.current_params.get("speed", 0.0)
            turn = self.current_params.get("turn", 0.0)
            self.context["gait"].set_target_speed(speed, turn)
            return True
        return False

class SetPose(ParameterLeaf):
    def run(self) -> bool:
        self._eval_params()
        if "gait" in self.context:
            pose = self.current_params.get("pose", "normal")
            self.context["gait"].set_pose(pose)
            return True
        return False

class SetCustomPose(ParameterLeaf):
    def run(self) -> bool:
        self._eval_params()
        if "gait" in self.context:
            # GaitSequencer will need a set_custom_pose or we update target_body_pose directly
            gait = self.context["gait"]
            for k, v in self.current_params.items():
                if k in gait.target_body_pose:
                    gait.target_body_pose[k] = v
            return True
        return False

BEHAVIOR_REGISTRY = {
    # Composites
    "Selector": Selector,
    "Sequence": Sequence,
    "Parallel": Parallel,
    "WeightedSelector": WeightedSelector,
    
    # Core Robot Actions
    "AvoidObstacles": AvoidObstacles,
    "SmartExplore": SmartExplore,
    "ReactToPerson": ReactToPerson,
    "FollowPerson": FollowPerson,
    "Idle": Idle,
    "HandleGesture": HandleGesture,
    "AlarmPulse": AlarmPulse,
    "SecurityMonitor": SecurityMonitor,
    "DogSocialInteraction": DogSocialInteraction,
    "PlayWithBall": PlayWithBall,
    "AmbientLook": AmbientLook,
    "ReactToFace": ReactToFace,
    "ExpressMood": ExpressMood,
    "AutoLevel": AutoLevel,
    "SniffAnimation": SniffAnimation,
    
    # Generic Parameter Actions
    "SetSpeed": SetSpeed,
    "SetPose": SetPose,
    "SetCustomPose": SetCustomPose,
    "AdditiveLayer": AdditiveLayer
}

class BehaviorFactory:
    def __init__(self, context: Dict[str, Any]):
        self.context = context

    def build_tree_from_file(self, file_path: str):
        try:
            with open(file_path, "r") as f:
                config = yaml.safe_load(f)
            return self.parse_node(config.get("root", {}))
        except Exception as e:
            logger.error(f"Failed to load behavior DNA from {file_path}: {e}")
            return Idle("FallbackIdle", self.context.get("gait"))

    def parse_node(self, node_cfg: Dict[str, Any]):
        node_type = node_cfg.get("type", "Idle")
        node_name = node_cfg.get("name", node_type)
        params = node_cfg.get("params", {})
        condition = node_cfg.get("condition")
        children_cfg = node_cfg.get("children", [])
        
        if node_type not in BEHAVIOR_REGISTRY:
            logger.warning(f"Unknown behavior node type: {node_type}")
            return Idle(f"Unknown_{node_name}", self.context.get("gait"))

        node_class = BEHAVIOR_REGISTRY[node_type]

        # 1. Handle WeightedSelector (Special Case)
        if node_type == "WeightedSelector":
            choices = []
            for child_cfg in children_cfg:
                # WeightedSelector expects children to be {weight, type, ...} or {choice: {weight, ...}}
                if "choice" in child_cfg:
                    cfg = child_cfg["choice"]
                    child_node = self.parse_node(cfg)
                    choices.append(WeightedChoice(
                        child_node, 
                        cfg.get("weight", 1.0), 
                        cfg.get("condition")
                    ))
            return WeightedSelector(node_name, choices, self.context)

        # 2. Handle Composites (Selector, Sequence, Parallel)
        if node_type in ["Selector", "Sequence", "Parallel"]:
            children = [self.parse_node(c) for c in children_cfg]
            # Some composites might need context for condition evaluation
            node = node_class(node_name, children)

        # 3. Handle ParameterLeaf (Actions that use self.current_params)
        elif issubclass(node_class, ParameterLeaf):
            # Special case for core nodes that might have legacy/odd signatures but are becoming ParameterLeafs
            if node_type == "AvoidObstacles":
                # We'll refactor AvoidObstacles to take (name, context, params)
                node = node_class(node_name, self.context, params)
            elif node_type == "SmartExplore":
                node = node_class(node_name, self.context, params)
            elif node_type == "Idle":
                 node = node_class(node_name, self.context, params)
            else:
                node = node_class(node_name, self.context, params)

        # 4. Handle Standard Behaviors (Legacy/Unchanged)
        else:
            try:
                # Fallback for nodes that are still just Leaf
                node = node_class(node_name, self.context)
            except Exception as e:
                logger.error(f"Error instantiating {node_type}: {e}")
                node = node_class(node_name, self.context.get("gait")) if "gait" in self.context else node_class(node_name)

        # --- CONDITION WRAPPING ---
        if condition:
            node = ConditionDecorator(f"Cond_{node_name}", node, condition, self.context)
            
        return node

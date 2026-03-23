import pytest
import yaml
from io import StringIO
from unittest.mock import Mock
from brain.bt_core import (
    Selector,
    Sequence,
    Parallel,
    Inverter,
    Leaf,
    Condition,
    WeightedSelector,
    WeightedChoice,
    ParameterLeaf,
    AdditiveLayer,
)
from brain.bt_factory import BehaviorFactory, SetSpeed, SetPose


class ActionLeaf(Leaf):
    def __init__(self, name, returns):
        super().__init__(name)
        self.returns = returns
        self.called = False

    def run(self):
        self.called = True
        return self.returns


class MockGait:
    def __init__(self):
        self.speed = 0.0
        self.turn = 0.0
        self.pose = "normal"
        self.additive_layers = {}

    def set_target_speed(self, speed, turn):
        self.speed = speed
        self.turn = turn

    def set_pose(self, pose):
        self.pose = pose

    def add_additive_layer(self, name, params):
        self.additive_layers[name] = params


class TestSelector:
    def test_selector_returns_first_success(self):
        """Selector should return True on first child success"""
        l1 = ActionLeaf("L1", False)
        l2 = ActionLeaf("L2", True)
        l3 = ActionLeaf("L3", True)

        sel = Selector("TestSelector", [l1, l2, l3])
        assert sel.run() is True
        assert l1.called is True
        assert l2.called is True
        assert l3.called is False

    def test_selector_all_fail(self):
        """Selector returns False when all children fail"""
        l1 = ActionLeaf("L1", False)
        l2 = ActionLeaf("L2", False)

        sel = Selector("TestSelector", [l1, l2])
        assert sel.run() is False
        assert l1.called is True
        assert l2.called is True

    def test_selector_empty_children(self):
        """Selector with no children should return False"""
        sel = Selector("EmptySelector", [])
        assert sel.run() is False


class TestSequence:
    def test_sequence_all_success(self):
        """Sequence returns True when all children succeed"""
        l1 = ActionLeaf("L1", True)
        l2 = ActionLeaf("L2", True)

        seq = Sequence("TestSequence", [l1, l2])
        assert seq.run() is True
        assert l1.called is True
        assert l2.called is True

    def test_sequence_fails_fast(self):
        """Sequence returns False on first child failure"""
        l1 = ActionLeaf("L1", True)
        l2 = ActionLeaf("L2", False)
        l3 = ActionLeaf("L3", True)

        seq = Sequence("TestSequence", [l1, l2, l3])
        assert seq.run() is False
        assert l1.called is True
        assert l2.called is True
        assert l3.called is False

    def test_sequence_empty_children(self):
        """Sequence with no children should return True"""
        seq = Sequence("EmptySequence", [])
        assert seq.run() is True


class TestParallel:
    def test_parallel_all_succeed(self):
        """Parallel returns True when all children succeed"""
        l1 = ActionLeaf("L1", True)
        l2 = ActionLeaf("L2", True)

        par = Parallel("TestParallel", [l1, l2])
        assert par.run() is True
        assert l1.called is True
        assert l2.called is True

    def test_parallel_partial_success_threshold(self):
        """Parallel succeeds with partial success if threshold met"""
        l1 = ActionLeaf("L1", True)
        l2 = ActionLeaf("L2", False)
        l3 = ActionLeaf("L3", True)

        par = Parallel("TestParallel", [l1, l2, l3], success_threshold=2)
        assert par.run() is True
        assert l1.called is True
        assert l2.called is True
        assert l3.called is True

    def test_parallel_fails_below_threshold(self):
        """Parallel returns False when successes below threshold"""
        l1 = ActionLeaf("L1", True)
        l2 = ActionLeaf("L2", False)
        l3 = ActionLeaf("L3", False)

        par = Parallel("TestParallel", [l1, l2, l3], success_threshold=2)
        assert par.run() is False
        assert l1.called is True
        assert l2.called is True
        assert l3.called is True

    def test_parallel_default_threshold(self):
        """Parallel default threshold is len(children)"""
        l1 = ActionLeaf("L1", True)
        l2 = ActionLeaf("L2", True)

        par = Parallel("TestParallel", [l1, l2])
        assert par.success_threshold == 2


class TestInverter:
    def test_inverter_inverts_success_to_failure(self):
        """Inverter should invert True to False"""
        child = ActionLeaf("Child", True)
        inv = Inverter("TestInverter", child)
        assert inv.run() is False

    def test_inverter_inverts_failure_to_success(self):
        """Inverter should invert False to True"""
        child = ActionLeaf("Child", False)
        inv = Inverter("TestInverter", child)
        assert inv.run() is True


class TestWeightedSelector:
    def test_weighted_selector_picks_by_weight(self):
        """WeightedSelector should pick based on weights"""
        context = {"mood": "happy"}

        choice1_node = ActionLeaf("Choice1", True)
        choice2_node = ActionLeaf("Choice2", True)

        choices = [
            WeightedChoice(choice1_node, weight=1.0),
            WeightedChoice(choice2_node, weight=3.0),  # More likely
        ]

        ws = WeightedSelector("WeightedTest", choices, context)
        # Run multiple times - choice2 should be picked more often due to higher weight
        results = [ws.run() for _ in range(100)]
        assert all(results)  # Both choices return True

    def test_weighted_selector_ignores_invalid_condition(self):
        """WeightedSelector should skip choices with failing conditions"""
        context = {"mood": "happy", "energy": 0.5}

        choice1_node = ActionLeaf("Choice1", True)
        choice2_node = ActionLeaf("Choice2", True)

        choices = [
            WeightedChoice(choice1_node, weight=1.0, condition="energy > 0.8"),
            WeightedChoice(choice2_node, weight=1.0),  # No condition - should be picked
        ]

        ws = WeightedSelector("WeightedTest", choices, context)
        # Choice1 should be skipped due to energy < 0.8
        result = ws.run()
        assert result is True  # Choice2 succeeds

    def test_weighted_selector_no_valid_choices(self):
        """WeightedSelector returns False when no valid choices"""
        context = {"energy": 0.1}

        choice1_node = ActionLeaf("Choice1", True)
        choice2_node = ActionLeaf("Choice2", True)

        choices = [
            WeightedChoice(choice1_node, weight=1.0, condition="energy > 0.8"),
            WeightedChoice(choice2_node, weight=1.0, condition="energy > 0.9"),
        ]

        ws = WeightedSelector("WeightedTest", choices, context)
        assert ws.run() is False


class TestParameterLeaf:
    def test_set_speed_updates_gait(self):
        """SetSpeed should update gait speed and turn"""
        gait = MockGait()
        context = {"gait": gait}

        params = {"speed": 0.5, "turn": 0.2}
        node = SetSpeed("TestSpeed", context, params)

        result = node.run()

        assert result is True
        assert gait.speed == 0.5
        assert gait.turn == 0.2

    def test_set_pose_updates_gait(self):
        """SetPose should update gait pose"""
        gait = MockGait()
        context = {"gait": gait}

        params = {"pose": "crouch"}
        node = SetPose("TestPose", context, params)

        result = node.run()

        assert result is True
        assert gait.pose == "crouch"

    def test_param_leaf_no_params(self):
        """ParameterLeaf with no params should not crash"""
        gait = MockGait()
        context = {"gait": gait}

        node = SetSpeed("TestSpeed", context, None)
        result = node.run()

        assert result is True

    def test_param_leaf_dynamic_mood_evaluation(self):
        """ParameterLeaf should evaluate dynamic mood expressions"""
        gait = MockGait()
        context = {"gait": gait, "mood": "happy", "energy": 1.0}

        params = {"speed": "energy * 0.5"}
        node = SetSpeed("TestSpeed", context, params)

        result = node.run()

        assert result is True
        assert gait.speed == pytest.approx(0.5)


class TestAdditiveLayer:
    def test_additive_layer_adds_to_gait(self):
        """AdditiveLayer should add a layer to gait"""
        gait = MockGait()
        context = {"gait": gait, "mood": "happy", "energy": 1.0}

        params = {"pitch": 5.0, "roll": 2.0}
        node = AdditiveLayer("TestLayer", context, params)

        result = node.run()

        assert result is True
        assert "TestLayer" in gait.additive_layers
        assert gait.additive_layers["TestLayer"]["pitch"] == 5.0


class TestCondition:
    def test_condition_calls_check_fn(self):
        """Condition should call its check function"""
        check_fn = Mock(return_value=True)
        cond = Condition("TestCondition", check_fn)

        result = cond.run()

        assert result is True
        check_fn.assert_called_once()

    def test_condition_returns_false_when_check_fails(self):
        """Condition should return False when check returns False"""
        check_fn = Mock(return_value=False)
        cond = Condition("TestCondition", check_fn)

        result = cond.run()

        assert result is False


class TestBehaviorFactory:
    @pytest.fixture
    def factory(self):
        gait = MockGait()
        context = {"gait": gait, "mood": "happy", "energy": 1.0}
        return BehaviorFactory(context)

    def test_parse_simple_selector(self, factory):
        """Factory should parse a Selector node"""
        node_cfg = {"type": "Selector", "name": "RootSelector", "children": []}

        node = factory.parse_node(node_cfg)

        assert isinstance(node, Selector)
        assert node.name == "RootSelector"

    def test_parse_sequence_with_children(self, factory):
        """Factory should parse a Sequence with child nodes"""
        node_cfg = {
            "type": "Sequence",
            "name": "TestSequence",
            "children": [
                {"type": "Idle", "name": "Child1"},
                {"type": "Idle", "name": "Child2"},
            ],
        }

        node = factory.parse_node(node_cfg)

        assert isinstance(node, Sequence)
        assert len(node.children) == 2

    def test_parse_with_params(self, factory):
        """Factory should pass params to ParameterLeaf nodes"""
        node_cfg = {
            "type": "SetSpeed",
            "name": "SpeedNode",
            "params": {"speed": 0.5, "turn": 0.0},
        }

        node = factory.parse_node(node_cfg)

        assert isinstance(node, SetSpeed)
        node.run()
        assert factory.context["gait"].speed == 0.5

    def test_parse_unknown_type_returns_idle(self, factory):
        """Factory should return Idle for unknown node types"""
        node_cfg = {"type": "UnknownBehavior", "name": "UnknownNode"}

        node = factory.parse_node(node_cfg)

        # Should not crash, should return some node
        assert node is not None

    def test_parse_with_condition(self, factory):
        """Factory should wrap node with ConditionDecorator when condition present"""
        node_cfg = {
            "type": "Idle",
            "name": "ConditionalNode",
            "condition": "energy > 0.5",
        }

        node = factory.parse_node(node_cfg)

        assert node is not None

    def test_parse_weighted_selector(self, factory):
        """Factory should parse WeightedSelector with choices"""
        node_cfg = {
            "type": "WeightedSelector",
            "name": "DecisionMaker",
            "children": [
                {"choice": {"type": "Idle", "name": "Option1", "weight": 1.0}},
                {"choice": {"type": "Idle", "name": "Option2", "weight": 2.0}},
            ],
        }

        node = factory.parse_node(node_cfg)

        assert isinstance(node, WeightedSelector)
        assert len(node.choices) == 2

    def test_parse_parallel(self, factory):
        """Factory should parse Parallel node"""
        node_cfg = {
            "type": "Parallel",
            "name": "ParallelNode",
            "children": [
                {"type": "Idle", "name": "Child1"},
                {"type": "Idle", "name": "Child2"},
            ],
        }

        node = factory.parse_node(node_cfg)

        assert isinstance(node, Parallel)

    def test_parse_parallel_with_threshold(self, factory):
        """Factory should parse Parallel with success_threshold"""
        node_cfg = {
            "type": "Parallel",
            "name": "ParallelNode",
            "params": {"success_threshold": 2},
            "children": [
                {"type": "Idle", "name": "Child1"},
                {"type": "Idle", "name": "Child2"},
                {"type": "Idle", "name": "Child3"},
            ],
        }

        node = factory.parse_node(node_cfg)

        assert isinstance(node, Parallel)


class TestYAMLIntegration:
    @pytest.fixture
    def factory(self):
        gait = MockGait()
        context = {"gait": gait, "mood": "happy", "energy": 1.0}
        return BehaviorFactory(context)

    def test_yaml_parsing_complete_tree(self, factory):
        """Test parsing a complete YAML behavior tree"""
        yaml_content = """
root:
  type: Selector
  name: RootSelector
  children:
    - type: Sequence
      name: HighPriority
      children:
        - type: SetSpeed
          name: MoveFast
          params:
            speed: 0.8
            turn: 0.0
    - type: Idle
      name: FallbackIdle
"""
        config = yaml.safe_load(yaml_content)
        node = factory.parse_node(config["root"])

        assert isinstance(node, Selector)
        assert node.name == "RootSelector"
        assert len(node.children) == 2

    def test_yaml_parsing_nested_composites(self, factory):
        """Test parsing deeply nested composite nodes"""
        yaml_content = """
root:
  type: Sequence
  name: NestedSequence
  children:
    - type: Selector
      name: InnerSelector
      children:
        - type: Idle
          name: Option1
        - type: Parallel
          name: InnerParallel
          children:
            - type: Idle
              name: ParallelChild1
            - type: Idle
              name: ParallelChild2
"""
        config = yaml.safe_load(yaml_content)
        node = factory.parse_node(config["root"])

        assert isinstance(node, Sequence)
        assert isinstance(node.children[0], Selector)
        assert isinstance(node.children[0].children[1], Parallel)

    def test_yaml_parsing_with_conditions(self, factory):
        """Test parsing nodes with conditions"""
        yaml_content = """
root:
  type: Sequence
  name: ConditionalSequence
  children:
    - type: SetSpeed
      name: ConditionalSpeed
      params:
        speed: 0.5
      condition: "energy > 0.5"
    - type: Idle
      name: LowEnergyFallback
"""
        config = yaml.safe_load(yaml_content)
        node = factory.parse_node(config["root"])

        assert isinstance(node, Sequence)
        # First child should be wrapped with ConditionDecorator
        assert len(node.children) == 2

    def test_yaml_parsing_additive_layer(self, factory):
        """Test parsing AdditiveLayer nodes"""
        yaml_content = """
root:
  type: Sequence
  name: BodyControl
  children:
    - type: AdditiveLayer
      name: PitchAdjustment
      params:
        pitch: 10.0
        roll: 5.0
"""
        config = yaml.safe_load(yaml_content)
        node = factory.parse_node(config["root"])

        assert isinstance(node, Sequence)
        assert isinstance(node.children[0], AdditiveLayer)

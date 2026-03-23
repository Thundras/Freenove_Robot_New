import pytest
import os
import tempfile
from unittest.mock import Mock
from brain.plugins import (
    register_plugin,
    get_plugin,
    get_all_plugins,
    load_plugins_from_directory,
    clear_plugins,
)
from brain.plugins.dance_behavior import DanceBehavior, PLUGIN_NAME


class MockGait:
    def __init__(self):
        self.speed = 0.0
        self.turn = 0.0
        self.pose = "normal"

    def set_target_speed(self, speed, turn=0.0):
        self.speed = speed
        self.turn = turn

    def set_pose(self, pose):
        self.pose = pose


class TestPluginRegistry:
    def setup_method(self):
        clear_plugins()

    def test_register_plugin(self):
        """Plugin should be registered and retrievable"""
        register_plugin("TestPlugin", Mock)
        assert "TestPlugin" in get_all_plugins()

    def test_get_plugin(self):
        """Should retrieve registered plugin by name"""
        register_plugin("MyPlugin", Mock)
        assert get_plugin("MyPlugin") == Mock

    def test_get_plugin_not_found(self):
        """Should raise KeyError for unknown plugin"""
        with pytest.raises(KeyError):
            get_plugin("NonExistent")

    def test_register_overwrites_existing(self):
        """Registering same name should overwrite"""
        register_plugin("Test", Mock)
        register_plugin("Test", str)
        assert get_plugin("Test") == str

    def test_get_all_plugins(self):
        """Should return copy of plugins dict"""
        register_plugin("A", Mock)
        register_plugin("B", str)
        plugins = get_all_plugins()
        assert "A" in plugins
        assert "B" in plugins

    def test_clear_plugins(self):
        """Should remove all registered plugins"""
        register_plugin("Test", Mock)
        clear_plugins()
        assert len(get_all_plugins()) == 0


class TestDanceBehavior:
    def setup_method(self):
        self.gait = MockGait()
        self.context = {"gait": self.gait}

    def test_dance_behavior_exists(self):
        """DanceBehavior should be importable"""
        assert DanceBehavior is not None

    def test_dance_behavior_params(self):
        """DanceBehavior should have PLUGIN_NAME and PLUGIN_CLASS"""
        assert PLUGIN_NAME == "DanceBehavior"
        assert DanceBehavior == DanceBehavior

    def test_dance_behavior_init(self):
        """DanceBehavior should initialize with params"""
        behavior = DanceBehavior(
            "TestDance", self.context, {"style": "wiggle", "duration": 1.0}
        )
        assert behavior.name == "TestDance"
        assert behavior.is_dancing is False

    def test_dance_behavior_run_no_gait(self):
        """Should return False when no gait in context"""
        context = {}
        behavior = DanceBehavior("Test", context, {})
        result = behavior.run()
        assert result is False

    def test_dance_behavior_start_dancing(self):
        """Should start dancing when not already dancing"""
        behavior = DanceBehavior(
            "TestDance", self.context, {"style": "wiggle", "duration": 10.0}
        )
        behavior.run()
        assert behavior.is_dancing is True

    def test_dance_behavior_style_wiggle(self):
        """Should set wiggle style parameters"""
        behavior = DanceBehavior(
            "TestDance", self.context, {"style": "wiggle", "duration": 10.0}
        )
        behavior.run()
        assert self.gait.speed > 0
        assert self.gait.turn != 0

    def test_dance_behavior_style_spin(self):
        """Should set spin style parameters"""
        behavior = DanceBehavior(
            "TestDance", self.context, {"style": "spin", "duration": 10.0}
        )
        behavior.run()
        assert self.gait.speed > 0
        assert self.gait.turn == 1.0

    def test_dance_behavior_style_bounce(self):
        """Should alternate poses for bounce style"""
        behavior = DanceBehavior(
            "TestDance", self.context, {"style": "bounce", "duration": 10.0}
        )
        behavior.run()
        assert self.gait.speed > 0


class TestPluginLoading:
    def setup_method(self):
        clear_plugins()

    def test_load_plugins_from_nonexistent_directory(self):
        """Should handle nonexistent directory gracefully"""
        loaded = load_plugins_from_directory("/nonexistent/path")
        assert loaded == []

    def test_load_plugins_finds_dance_behavior(self):
        """Should find DanceBehavior plugin in plugins directory"""
        plugins_dir = os.path.join(os.path.dirname(__file__), "..", "brain", "plugins")
        loaded = load_plugins_from_directory(plugins_dir)
        assert "DanceBehavior" in loaded
        assert "DanceBehavior" in get_all_plugins()

    def test_dance_behavior_usable_after_load(self):
        """DanceBehavior should be usable after loading"""
        plugins_dir = os.path.join(os.path.dirname(__file__), "..", "brain", "plugins")
        load_plugins_from_directory(plugins_dir)

        gait = MockGait()
        context = {"gait": gait}
        behavior = get_plugin("DanceBehavior")("Test", context, {"duration": 10.0})

        assert behavior.run() is True


class TestPluginIntegration:
    def setup_method(self):
        clear_plugins()

    def test_plugin_with_bt_factory(self):
        """Plugin should work with BehaviorFactory"""
        from brain.bt_factory import load_plugins_from_config, get_full_registry

        plugins_dir = os.path.join(os.path.dirname(__file__), "..", "brain", "plugins")
        load_plugins_from_directory(plugins_dir)

        registry = get_full_registry()
        assert "DanceBehavior" in registry
        assert registry["DanceBehavior"] == DanceBehavior

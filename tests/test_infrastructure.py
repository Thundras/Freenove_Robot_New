import pytest
from utils.plugin_loader import PluginLoader

class MockRobot:
    def __init__(self):
        self.plugin_called = False

def test_plugin_loader_empty():
    """Verify loader handles empty plugin directory"""
    loader = PluginLoader()
    robot = MockRobot()
    # Should not crash
    loader.load_plugins(robot)
    assert not robot.plugin_called

def test_plugin_loading():
    """Verify loader can scan directory"""
    loader = PluginLoader(plugin_dir="plugins")
    robot = MockRobot()
    # load_plugins returns number of loaded plugins
    count = loader.load_plugins(robot)
    assert isinstance(count, int)

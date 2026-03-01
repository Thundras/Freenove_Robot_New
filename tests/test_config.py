import pytest
import os
from utils.config import ConfigManager

def test_config_loading(tmp_path):
    """Verify that config can be loaded from file"""
    d = tmp_path / "config"
    d.mkdir()
    p = d / "config.yaml"
    p.write_text("system:\n  control_loop_hz: 100\n")
    
    config = ConfigManager(config_path=str(p))
    assert config.get("system.control_loop_hz") == 100

def test_config_override(tmp_path):
    """Verify that config values can be retrieved with paths"""
    p = tmp_path / "empty.yaml"
    p.write_text("test_key: 123")
    config = ConfigManager(config_path=str(p))
    assert config.get("test_key") == 123
    assert config.get("non_existent", "default") == "default"

"""
Plugin System for Behavior Tree Nodes.

Allows adding custom behaviors without modifying core code.
"""

import logging
import importlib
import os
from typing import Dict, Type, Any, List

logger = logging.getLogger(__name__)

_PLUGINS: Dict[str, Type] = {}


def register_plugin(name: str, node_class: Type) -> None:
    """
    Register a custom behavior node plugin.

    Args:
        name: Unique identifier for the plugin (e.g., "MyCustomBehavior")
        node_class: The behavior node class to register
    """
    if name in _PLUGINS:
        logger.warning(f"Plugin '{name}' already registered, overwriting.")
    _PLUGINS[name] = node_class
    logger.info(f"Registered plugin: {name}")


def get_plugin(name: str) -> Type:
    """Get a registered plugin by name."""
    if name not in _PLUGINS:
        raise KeyError(f"Plugin '{name}' not found. Available: {list(_PLUGINS.keys())}")
    return _PLUGINS[name]


def get_all_plugins() -> Dict[str, Type]:
    """Get all registered plugins."""
    return _PLUGINS.copy()


def load_plugins_from_directory(directory: str) -> List[str]:
    """
    Auto-load all Python modules from a directory as plugins.

    Each module should define a PLUGIN_CLASS variable with the behavior class.

    Args:
        directory: Path to plugins directory

    Returns:
        List of loaded plugin names
    """
    loaded = []

    if not os.path.isdir(directory):
        logger.warning(f"Plugin directory not found: {directory}")
        return loaded

    for filename in os.listdir(directory):
        if filename.startswith("_") or not filename.endswith(".py"):
            continue

        module_name = filename[:-3]
        try:
            module = importlib.import_module(f"brain.plugins.{module_name}")

            if hasattr(module, "PLUGIN_CLASS"):
                plugin_class = module.PLUGIN_CLASS
                plugin_name = getattr(module, "PLUGIN_NAME", module_name)
                register_plugin(plugin_name, plugin_class)
                loaded.append(plugin_name)
                logger.info(f"Loaded plugin from {module_name}: {plugin_name}")
            else:
                logger.warning(f"Module {module_name} has no PLUGIN_CLASS defined")

        except Exception as e:
            logger.error(f"Failed to load plugin {module_name}: {e}")

    return loaded


def clear_plugins() -> None:
    """Clear all registered plugins. Useful for testing."""
    _PLUGINS.clear()

import os
import importlib.util
import logging
from typing import List, Any

logger = logging.getLogger(__name__)

class PluginLoader:
    def __init__(self, plugin_dir: str = "plugins"):
        self.plugin_dir = plugin_dir
        self.plugins: List[Any] = []
        
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)
            logger.info(f"Created plugin directory: {self.plugin_dir}")

    def load_plugins(self, context: Any) -> int:
        """
        Dynamically loads all .py files from the plugin directory.
        Each plugin should have an 'initialize(context)' function.
        """
        count = 0
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                plugin_name = filename[:-3]
                file_path = os.path.join(self.plugin_dir, filename)
                
                try:
                    spec = importlib.util.spec_from_file_location(plugin_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        if hasattr(module, "initialize"):
                            module.initialize(context)
                            self.plugins.append(module)
                            logger.info(f"Plugin loaded and initialized: {plugin_name}")
                            count += 1
                        else:
                            logger.warning(f"Plugin {plugin_name} is missing 'initialize' function.")
                except Exception as e:
                    logger.error(f"Failed to load plugin {plugin_name}: {e}")
                    
        return count

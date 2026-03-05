import yaml
import os
import threading
from typing import Any, Dict

class ConfigManager:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._last_mtime = 0
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with self._lock:
            self._last_mtime = os.path.getmtime(self.config_path)
            with open(self.config_path, "r") as f:
                self._config = yaml.safe_load(f)

    def reload_if_changed(self):
        """Check if config file has changed on disk and reload if necessary"""
        if not os.path.exists(self.config_path):
            return
            
        current_mtime = os.path.getmtime(self.config_path)
        if current_mtime > self._last_mtime:
            print(f"Config change detected on disk. Reloading {self.config_path}...")
            self.load_config()
            return True
        return False

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        val = self._config
        try:
            for k in keys:
                val = val[k]
            return val
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any):
        """Update a config value in memory (supports dot notation)"""
        with self._lock:
            keys = key.split(".")
            d = self._config
            for k in keys[:-1]:
                if k not in d or not isinstance(d[k], dict):
                    d[k] = {}
                d = d[k]
            d[keys[-1]] = value

    def save_config(self):
        """Persist current configuration to disk"""
        with self._lock:
            try:
                with open(self.config_path, "w") as f:
                    yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
                return True
            except Exception as e:
                print(f"Error saving config: {e}")
                return False

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_lock']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._lock = threading.Lock()

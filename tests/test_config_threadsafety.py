import pytest
import threading
import time
from utils.config import ConfigManager


class TestThreadSafeConfig:
    def test_config_has_lock(self):
        config = ConfigManager()
        assert hasattr(config, "_lock")
        assert isinstance(config._lock, type(threading.Lock()))

    def test_get_is_thread_safe(self):
        config = ConfigManager()
        errors = []

        def reader():
            try:
                for _ in range(100):
                    val = config.get("system.control_loop_hz")
                    assert val is not None
            except Exception as e:
                errors.append(str(e))

        def writer():
            try:
                for i in range(100):
                    config.set("system.test_value", i)
            except Exception as e:
                errors.append(str(e))

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_get_operations(self):
        config = ConfigManager()
        results = []

        def reader():
            for _ in range(50):
                val = config.get("system.control_loop_hz")
                results.append(val)

        threads = [threading.Thread(target=reader) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 250
        assert all(r == 75 for r in results)

    def test_concurrent_set_operations(self):
        config = ConfigManager()

        def writer(thread_id):
            for i in range(20):
                config.set(f"system.thread_{thread_id}", i)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for i in range(4):
            assert config.get(f"system.thread_{i}") == 19

    def test_reload_preserves_thread_safety(self):
        config = ConfigManager()
        errors = []

        def reader():
            try:
                for _ in range(50):
                    config.get("system.control_loop_hz")
            except Exception as e:
                errors.append(str(e))

        def reloader():
            try:
                for _ in range(5):
                    config.reload_if_changed()
            except Exception as e:
                errors.append(str(e))

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=reader),
            threading.Thread(target=reloader),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_get_with_nested_keys(self):
        config = ConfigManager()
        val = config.get("battery.voltage_min")
        assert val == 7.0

        val_default = config.get("nonexistent.key", "default")
        assert val_default == "default"

    def test_set_with_nested_keys(self):
        config = ConfigManager()
        config.set("battery.new_setting", 123)
        assert config.get("battery.new_setting") == 123

        config.set("system.nested.deep.value", 456)
        assert config.get("system.nested.deep.value") == 456

    def test_no_deadlock_on_reload(self):
        config = ConfigManager()

        def reader():
            for _ in range(20):
                config.get("system.control_loop_hz")

        def reloader():
            for _ in range(20):
                config.reload_if_changed()

        t1 = threading.Thread(target=reader)
        t2 = threading.Thread(target=reloader)

        start = time.time()
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        elapsed = time.time() - start

        assert elapsed < 2.0

    def test_config_pickle_safety(self):
        config = ConfigManager()
        import pickle

        config.set("system.test_pickle", "value")
        pickled = pickle.dumps(config)
        restored = pickle.loads(pickled)

        assert restored.get("system.test_pickle") == "value"
        assert hasattr(restored, "_lock")

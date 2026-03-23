import pytest
import multiprocessing
import time
from utils.config import ConfigManager


class TestQueueTimeout:
    def test_queue_timeout_config(self):
        config = ConfigManager()
        timeout = config.get("system.queue_consumer_timeout", 0.01)
        assert timeout == 0.01
        assert timeout > 0

    def test_max_queue_items_config(self):
        config = ConfigManager()
        max_items = config.get("system.max_queue_items_per_update", 3)
        assert max_items == 3
        assert max_items > 0

    def test_queue_get_with_timeout(self):
        queue = multiprocessing.Queue()
        start = time.time()
        try:
            queue.get(timeout=0.01)
        except:
            pass
        elapsed = time.time() - start
        assert elapsed < 0.05

    def test_queue_maxsize_prevents_bloat(self):
        queue = multiprocessing.Queue(maxsize=10)
        for i in range(15):
            try:
                queue.put_nowait(i)
            except:
                pass
        assert queue.qsize() <= 10

    def test_queue_nonblocking_put(self):
        queue = multiprocessing.Queue(maxsize=2)
        queue.put_nowait("item1")
        queue.put_nowait("item2")
        with pytest.raises(Exception):
            queue.put_nowait("item3")

    def test_queue_empty_get_nonblocking(self):
        queue = multiprocessing.Queue()
        with pytest.raises(Exception):
            queue.get_nowait()

    def test_queue_timeout_after_data(self):
        queue = multiprocessing.Queue()
        queue.put_nowait("data")
        start = time.time()
        item = queue.get(timeout=1.0)
        elapsed = time.time() - start
        assert item == "data"
        assert elapsed < 0.1

    def test_queue_multiple_items_with_limit(self):
        queue = multiprocessing.Queue()
        for i in range(10):
            queue.put_nowait(i)

        items = []
        max_items = 3
        for _ in range(max_items):
            try:
                items.append(queue.get_nowait())
            except:
                break

        assert len(items) <= 3
        remaining = 0
        for _ in range(10):
            try:
                queue.get_nowait()
                remaining += 1
            except:
                break
        assert remaining >= 6

    def test_queue_fairness_multiple_producers(self):
        queue = multiprocessing.Queue(maxsize=5)
        for i in range(5):
            queue.put_nowait(f"producer_{i}")

        consumed = []
        for _ in range(5):
            try:
                consumed.append(queue.get_nowait())
            except:
                break

        assert len(consumed) == 5
        assert all("producer_" in str(c) for c in consumed)

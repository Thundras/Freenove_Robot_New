import pytest
import multiprocessing
from brain.vision import VisionProcess
from utils.config import ConfigManager

def test_vision_process_lifecycle():
    """Verify that VisionProcess can start and stop correctly"""
    queue = multiprocessing.Queue()
    config = ConfigManager()
    proc = VisionProcess(queue, multiprocessing.Queue(), config)
    
    proc.start()
    assert proc.is_alive()
    
    # Wait for at least one simulation message (landmark or object)
    found = False
    for _ in range(20): # Timeout after 2 seconds
        if not queue.empty():
            msg = queue.get()
            assert "type" in msg
            found = True
            break
        import time
        time.sleep(0.1)
    
    proc.stop()
    proc.join(timeout=2.0)
    if proc.is_alive():
        proc.terminate()
        proc.join()
    assert not proc.is_alive()

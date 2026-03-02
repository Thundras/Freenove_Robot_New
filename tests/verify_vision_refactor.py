import multiprocessing
import time
import logging
from brain.vision import VisionProcess
from utils.config import ConfigManager

logging.basicConfig(level=logging.INFO)

def test_vision_initialization():
    print("--- Testing Vision Process (Tasks API) Initialization ---")
    result_queue = multiprocessing.Queue()
    frame_queue = multiprocessing.Queue()
    config = ConfigManager()
    
    # Enable debug logs for this test
    logging.getLogger("brain.vision").setLevel(logging.DEBUG)
    
    proc = VisionProcess(result_queue, frame_queue, config)
    proc.start()
    
    time.sleep(5) # Give it time to initialize
    
    is_alive = proc.is_alive()
    print(f"Vision Process Alive: {is_alive}")
    
    # Check if we got any "loaded successfully" or error logs in the console
    # (We can't easily capture logs from a separate process here without more piping, 
    # but we can check if it crashed).
    
    proc.stop()
    proc.join(timeout=2)
    if proc.is_alive():
        proc.terminate()
    print("Test complete.")

if __name__ == "__main__":
    test_vision_initialization()

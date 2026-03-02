import logging
import multiprocessing
import time
import os
import sys

# Silence logs for this test runner
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestShutdown")

from brain.vision import VisionProcess
from utils.config import ConfigManager

def test_vision_shutdown():
    config = ConfigManager()
    result_queue = multiprocessing.Queue()
    frame_queue = multiprocessing.Queue(maxsize=1)
    
    logger.info("Starting VisionProcess for shutdown test...")
    vision = VisionProcess(result_queue, frame_queue, config)
    vision.start()
    
    # Let it run for a bit to initialize models
    time.sleep(5) 
    
    logger.info("Requesting VisionProcess stop...")
    vision.stop()
    
    start_time = time.time()
    vision.join(timeout=5.0)
    
    if vision.is_alive():
        logger.error("VisionProcess FAILED to stop gracefully within 5 seconds.")
        vision.terminate()
        sys.exit(1)
    else:
        logger.info(f"VisionProcess stopped gracefully in {time.time() - start_time:.2f} seconds.")
        sys.exit(0)

if __name__ == "__main__":
    test_vision_shutdown()

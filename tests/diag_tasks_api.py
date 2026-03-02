import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import os

def check_tasks_api():
    print("--- Vision Tasks API Diagnostics ---")
    
    # 1. Check if we can import the classes
    try:
        base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
        print("MediaPipe Tasks imported successfully.")
    except Exception as e:
        print(f"FAILED to import MediaPipe Tasks: {e}")
        return

    # 2. Check if we can at least initialize a Detector (requires model file)
    # We won't actually run it without the .task file, but we check if the API is there.
    print(f"MediaPipe Version: {mp.__version__}")
    if hasattr(vision, 'HandLandmarker'):
        print("HandLandmarker class is available.")
    else:
        print("HandLandmarker class MISSING from vision tasks.")

if __name__ == "__main__":
    check_tasks_api()

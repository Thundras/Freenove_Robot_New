import cv2
import mediapipe as mp
import time

def check_vision_stack():
    print("--- Vision Stack Diagnostics ---")
    
    # 1. Check OpenCV
    print(f"OpenCV Version: {cv2.__version__}")
    
    # 2. Check MediaPipe
    print(f"MediaPipe Version: {mp.__version__}")
    mp_hands = mp.solutions.hands
    try:
        hands = mp_hands.Hands(
            static_image_mode=True,
            max_num_hands=1,
            min_detection_confidence=0.5
        )
        print("MediaPipe Hands initialized successfully.")
    except Exception as e:
        print(f"FAILED to initialize MediaPipe Hands: {e}")
        return

    # 3. Check Camera
    print("Attempting to open camera 0...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("FAILED to open camera 0.")
        return
    
    ret, frame = cap.read()
    if not ret:
        print("FAILED to read frame from camera.")
    else:
        print(f"Successfully captured frame: {frame.shape}")
        
    cap.release()
    print("Diagnostics complete.")

if __name__ == "__main__":
    check_vision_stack()

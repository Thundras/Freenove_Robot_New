import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision as mp_vision
import time
import os

def diag_gestures():
    print("--- MediaPipe HandLandmarker Live Diag ---")
    
    model_path = "brain/models/hand_landmarker.task"
    if not os.path.exists(model_path):
        print(f"ERROR: Model not found at {model_path}")
        return

    base_options = python.BaseOptions(model_asset_path=model_path)
    options = mp_vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.5, # Lowered for testing
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    print("Initializing HandLandmarker...")
    detector = mp_vision.HandLandmarker.create_from_options(options)
    
    cap = cv2.VideoCapture(0)
    print("Camera opened. Show your hand!")
    
    last_ts = 0
    start_time = time.time()
    
    try:
        while time.time() - start_time < 15: # Run for 15s
            ret, frame = cap.read()
            if not ret: break
            
            # Convert to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            ts = int(time.time() * 1000)
            if ts <= last_ts: ts = last_ts + 1
            last_ts = ts
            
            results = detector.detect_for_video(mp_image, ts)
            
            if results.hand_landmarks:
                print(f"Hand Detected! (Confidence not directly visible in results, but it's there)")
                for hand_landmarks in results.hand_landmarks:
                    # Check Index Finger (Landmarks 5, 8)
                    wrist = hand_landmarks[0]
                    index_tip = hand_landmarks[8]
                    index_pip = hand_landmarks[6]
                    
                    dist_tip = ((index_tip.x - wrist.x)**2 + (index_tip.y - wrist.y)**2)**0.5
                    dist_pip = ((index_pip.x - wrist.x)**2 + (index_pip.y - wrist.y)**2)**0.5
                    ratio = dist_tip / dist_pip if dist_pip > 0 else 0
                    print(f"  Index Tip Ratio: {ratio:.2f}")
            
            cv2.imshow("Hand Diag (Press 'q' to quit early)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        detector.close()
        cap.release()
        cv2.destroyAllWindows()
        print("Done.")

if __name__ == "__main__":
    diag_gestures()

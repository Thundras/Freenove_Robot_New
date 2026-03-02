import cv2
import os
import sys

def check_face_api():
    print("--- OpenCV Face API Diagnostics ---")
    print(f"OpenCV Version: {cv2.__version__}")
    
    # 1. Check classes
    if hasattr(cv2, 'FaceDetectorYN'):
        print("FaceDetectorYN: AVAILABLE")
    else:
        print("FaceDetectorYN: MISSING")
        
    if hasattr(cv2, 'FaceRecognizerSF'):
        print("FaceRecognizerSF: AVAILABLE")
    else:
        print("FaceRecognizerSF: MISSING")

    # 2. Try to create detector
    detector_path = "brain/models/face_detection_yunet.onnx"
    recognizer_path = "brain/models/face_recognition_sface.onnx"
    
    if os.path.exists(detector_path):
        print(f"Detector model found: {detector_path}")
        try:
            detector = cv2.FaceDetectorYN.create(detector_path, "", (320, 320))
            print("Detector created successfully.")
        except Exception as e:
            print(f"FAILED to create detector: {e}")
    else:
        print(f"Detector model NOT FOUND: {detector_path}")

    if os.path.exists(recognizer_path):
        print(f"Recognizer model found: {recognizer_path}")
        try:
            recognizer = cv2.FaceRecognizerSF.create(recognizer_path, "")
            print("Recognizer created successfully.")
        except Exception as e:
            print(f"FAILED to create recognizer: {e}")
    else:
        print(f"Recognizer model NOT FOUND: {recognizer_path}")

if __name__ == "__main__":
    check_face_api()

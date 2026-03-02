import pytest
import numpy as np

def calculate_fingers(landmarks):
    """
    Simulated implementation of the logic in vision.py
    landmarks: list of (x, y) tuples
    """
    fingers = []
    wrist = landmarks[0]
    
    for tip_id in [8, 12, 16, 20]:
        tip = landmarks[tip_id]
        knuckle = landmarks[tip_id - 2]
        
        dist_tip = ((tip[0] - wrist[0])**2 + (tip[1] - wrist[1])**2)**0.5
        dist_knuckle = ((knuckle[0] - wrist[0])**2 + (knuckle[1] - wrist[1])**2)**0.5
        
        if dist_tip > dist_knuckle * 1.3:
            fingers.append(1)
            
    return sum(fingers)

def test_finger_counting_vertical():
    # Wrist at (0,0)
    # Fingers extended vertically (negative y)
    landmarks = [(0, 0)] * 21
    # Index finger
    landmarks[6] = (0, -0.2) # Knuckle
    landmarks[8] = (0, -0.3) # Tip
    # Ratio: 0.3 / 0.2 = 1.5 > 1.3 (Extended)
    
    assert calculate_fingers(landmarks) == 1

def test_finger_counting_horizontal():
    # Wrist at (0,0)
    # Fingers extended horizontally
    landmarks = [(0, 0)] * 21
    # Index finger
    landmarks[6] = (0.2, 0) # Knuckle
    landmarks[8] = (0.3, 0) # Tip
    # Ratio: 0.3 / 0.2 = 1.5 > 1.3 (Extended)
    
    assert calculate_fingers(landmarks) == 1

def test_finger_counting_closed():
    # Wrist at (0,0)
    # Fingers curled
    landmarks = [(0, 0)] * 21
    # Index finger tip is closer to wrist than knuckle
    landmarks[6] = (0, -0.2) # Knuckle
    landmarks[8] = (0, -0.1) # Tip (curled)
    # Ratio: 0.1 / 0.2 = 0.5 < 1.3 (Not Extended)
    
    assert calculate_fingers(landmarks) == 0

def test_gesture_labels():
    # Logic from vision.py:
    # 3+ -> COME, 2 -> SIT, 1 -> DOWN, 0 -> AWAY
    
    def get_label(count):
        if count >= 3: return "COME"
        if count == 2: return "SIT"
        if count == 1: return "DOWN"
        return "AWAY"

    assert get_label(4) == "COME"
    assert get_label(3) == "COME"
    assert get_label(2) == "SIT"
    assert get_label(1) == "DOWN"
    assert get_label(0) == "AWAY"

import unittest
import json
import logging
import sys
import os

# Add parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.web_server import WebServer
from brain.intelligence import IntelligenceController
from utils.config import ConfigManager

# Mock classes to avoid hardware dependencies
class MockGait:
    def __init__(self):
        self.current_pose = "normal"
        self.target_speed = 0.0
    def set_pose(self, pose): 
        self.current_pose = pose
    def set_target_speed(self, speed, turn=0.0): 
        self.target_speed = speed

class MockSensor:
    def update(self): pass
    def get_data(self): return None
    def clear(self): pass

class TestApiModeSwitching(unittest.TestCase):
    def setUp(self):
        # Suppress logging during tests
        logging.getLogger('brain.behaviors').setLevel(logging.ERROR)
        logging.getLogger('brain.intelligence').setLevel(logging.ERROR)
        logging.getLogger('api.web_server').setLevel(logging.ERROR)
        
        config = ConfigManager()
        self.gait = MockGait()
        self.sensors = {
            "battery": MockSensor(), 
            "led": MockSensor(),
            "ultrasonic": MockSensor()
        }
        self.intelligence = IntelligenceController(config, sensors=self.sensors, gait=self.gait)
        self.web = WebServer(config, movement_engine=self.gait, intelligence=self.intelligence)
        self.app = self.web.app.test_client()

    def find_node(self, name):
        """Helper to find a node in the BT by name"""
        # Search in root children (Selector)
        for child in self.intelligence.root.children:
            if child.name == name:
                return child
            # Recursive check if it's a composite
            if hasattr(child, "children"):
                for sub in child.children:
                    if sub.name == name:
                        return sub
        return None

    def test_pose_to_mode_mapping(self):
        # 1. Start in autonomous
        self.intelligence.context["system_mode"] = "autonomous"
        explore_node = self.find_node("SmartExplore")
        self.assertIsNotNone(explore_node)
        
        # 2. Test 'sit' pose sets 'sit' mode via API
        response = self.app.post('/api/pose/sit')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.intelligence.context["system_mode"], "sit")
        self.assertEqual(self.gait.current_pose, "sit")
        
        # Verify behavior 'ExploreRoom' is suppressed
        self.assertFalse(explore_node.run(), "ExploreRoom should return False when mode is SIT")

        # 3. Test 'down' pose sets 'down' mode
        self.app.post('/api/pose/down')
        self.assertEqual(self.intelligence.context["system_mode"], "down")
        self.assertFalse(explore_node.run(), "ExploreRoom should return False when mode is DOWN")

        # 4. Test 'normal' pose sets 'autonomous' mode
        self.app.post('/api/pose/normal')
        self.assertEqual(self.intelligence.context["system_mode"], "autonomous")
        self.assertTrue(explore_node.run(), "ExploreRoom should return True when mode is AUTONOMOUS")

    def test_mode_change_via_api(self):
        # Direct mode change to 'manual'
        self.app.post('/api/mode/manual')
        self.assertEqual(self.intelligence.context["system_mode"], "manual")
        
        # Verify PlayWithBall is suppressed
        ball_node = self.find_node("PlayWithBall")
        self.assertIsNotNone(ball_node)
        self.assertFalse(ball_node.run(), "PlayWithBall should return False in MANUAL mode")

        # Verify FollowPerson is suppressed
        follow_node = self.find_node("FollowPerson")
        self.assertIsNotNone(follow_node)
        self.assertFalse(follow_node.run(), "FollowPerson should return False in MANUAL mode")

if __name__ == '__main__':
    unittest.main()

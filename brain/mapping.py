import logging
import math
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class MappingManager:
    """
    Pillar 3: Visual SLAM Light.
    Combines Odometry (Steps), Ultrasonic (Obstacles), and Vision (Landmarks).
    """
    def __init__(self):
        self.grid = {} # Map coordinates to occupancy
        self.landmarks: Dict[int, Tuple[float, float]] = {} # id -> (x, y) world coordinates
        self.robot_pos = [0.0, 0.0] # (x, y) in mm
        self.robot_yaw = 0.0 # Orientation in radians

    def update_odometry(self, dx: float, dy: float, dyaw: float):
        """Standard dead reckoning based on step increments"""
        # Transform local movement to world coordinates based on current yaw
        world_dx = dx * math.cos(self.robot_yaw) - dy * math.sin(self.robot_yaw)
        world_dy = dx * math.sin(self.robot_yaw) + dy * math.cos(self.robot_yaw)
        
        self.robot_pos[0] += world_dx
        self.robot_pos[1] += world_dy
        self.robot_yaw += dyaw
        
    def add_landmark(self, marker_id: int, distance: float, angle_rel: float):
        """
        Visual SLAM: Use Aruco markers to correct position or build map.
        If landmark is known, we could perform re-localization.
        If unknown, we add it to the map.
        """
        # Calculate world position of the landmark
        world_angle = self.robot_yaw + angle_rel
        lx = self.robot_pos[0] + distance * math.cos(world_angle)
        ly = self.robot_pos[1] + distance * math.sin(world_angle)
        
        if marker_id not in self.landmarks:
            self.landmarks[marker_id] = (lx, ly)
            logger.info(f"New Visual Landmark found: ID {marker_id} at ({lx:.1f}, {ly:.1f})")
        else:
            # Re-localization logic would go here: 
            # adjust robot_pos based on known landmark location
            known_lx, known_ly = self.landmarks[marker_id]
            # logger.debug(f"Seeing known landmark {marker_id}. Correction possible.")

    def add_obstacle(self, dist: float, angle_rel: float):
        """Adds ultrasonic detection to the grid map"""
        world_angle = self.robot_yaw + angle_rel
        ox = self.robot_pos[0] + dist * math.cos(world_angle)
        oy = self.robot_pos[1] + dist * math.sin(world_angle)
        
        # Simple rounding to 1cm grid
        grid_pos = (int(ox / 10), int(oy / 10))
        self.grid[grid_pos] = 1 # Occupied

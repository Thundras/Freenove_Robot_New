import logging
import math
import time
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class MappingManager:
    """
    Pillar 3: Visual SLAM Light.
    Combines Odometry (Steps), Ultrasonic (Obstacles), and Vision (Landmarks).
    Supports dynamic environments via Ray-Clearing and Aging.
    """
    def __init__(self):
        self.grid = {} # Map coordinates (cm) -> last_seen_timestamp
        self.landmarks: Dict[int, Tuple[float, float, float]] = {} # id -> (x, y, yaw) world coordinates
        self.robot_pos = [0.0, 0.0] # (x, y) in mm
        self.robot_yaw = 0.0 # Orientation in radians

    def update_odometry(self, dx: float, dy: float, dyaw: float):
        """Standard dead reckoning based on step increments"""
        world_dx = dx * math.cos(self.robot_yaw) - dy * math.sin(self.robot_yaw)
        world_dy = dx * math.sin(self.robot_yaw) + dy * math.cos(self.robot_yaw)
        
        self.robot_pos[0] += world_dx
        self.robot_pos[1] += world_dy
        self.robot_yaw += dyaw
        
    def add_landmark(self, marker_id: int, distance: float, angle_rel: float, marker_yaw_rel: float = 0.0):
        """Visual SLAM: Use Aruco markers to build map or re-localize"""
        world_angle = self.robot_yaw + angle_rel
        lx = self.robot_pos[0] + distance * math.cos(world_angle)
        ly = self.robot_pos[1] + distance * math.sin(world_angle)
        
        # World orientation of the marker
        world_yaw = self.robot_yaw + angle_rel + marker_yaw_rel
        
        if marker_id not in self.landmarks:
            self.landmarks[marker_id] = (lx, ly, world_yaw)
            logger.info(f"New Visual Landmark: ID {marker_id} at ({lx:.1f}, {ly:.1f}) yaw={math.degrees(world_yaw):.1f}°")

    def add_obstacle(self, dist_mm: float, angle_rel: float):
        """Adds ultrasonic detection to the grid map with timestamp"""
        world_angle = self.robot_yaw + angle_rel
        ox = self.robot_pos[0] + dist_mm * math.cos(world_angle)
        oy = self.robot_pos[1] + dist_mm * math.sin(world_angle)
        
        grid_pos = (int(ox / 50), int(oy / 50))
        self.grid[grid_pos] = time.time() # 1 = Occupied + Timestamp

    def clear_path(self, dist_mm: float, angle_rel: float):
        """
        Ray-Clearing: Removes obstacles in the path that are no longer there.
        Iterates from robot to dist_mm and deletes grid entries.
        """
        world_angle = self.robot_yaw + angle_rel
        # Step in 5cm increments to clear the path
        for d in range(50, int(dist_mm), 50):
            cx = self.robot_pos[0] + d * math.cos(world_angle)
            cy = self.robot_pos[1] + d * math.sin(world_angle)
            grid_pos = (int(cx / 50), int(cy / 50))
            if grid_pos in self.grid:
                del self.grid[grid_pos]

    def cleanup_old_points(self, max_age_seconds: float = 300):
        """Removes points that haven't been confirmed for a while"""
        now = time.time()
        to_delete = [pos for pos, ts in self.grid.items() if now - ts > max_age_seconds]
        for pos in to_delete:
            del self.grid[pos]
        if to_delete:
            logger.debug(f"Map Aging: Cleaned up {len(to_delete)} stale points.")

    def is_safe_spot(self) -> bool:
        """
        Heuristic: Is the robot currently in a 'polite' resting location?
        1. Near a wall or object (within 15-40cm).
        2. Not blocking a narrow passage (checked via local grid density).
        """
        # 1. Check proximity to nearest obstacle
        min_dist = 1000.0
        for pos, ts in self.grid.items():
            ox, oy = pos[0]*50, pos[1]*50
            dist = math.sqrt((ox - self.robot_pos[0])**2 + (oy - self.robot_pos[1])**2)
            if dist < min_dist: min_dist = dist
        
        # Too far from wall (exposed) or too close (collision/cramped)
        if min_dist > 500 or min_dist < 100:
            return False
            
        # 2. Check occupancy density in a 40cm radius
        nearby_points = 0
        radius_cm = 40
        for dx in range(-int(radius_cm/5), int(radius_cm/5) + 1):
            for dy in range(-int(radius_cm/5), int(radius_cm/5) + 1):
                check_pos = (int(self.robot_pos[0]/50) + dx, int(self.robot_pos[1]/50) + dy)
                if check_pos in self.grid:
                    nearby_points += 1
        
        # If too many points (e.g. > 15), it's likely a crowded area or corner
        if nearby_points > 15:
            return False
            
        return True

    def is_near_wall(self) -> bool:
        """Returns True if any mapped points are within 40cm of the robot"""
        for pos, ts in self.grid.items():
            ox, oy = pos[0]*50, pos[1]*50 # grid is in 5cm units, pos is index
            dist = math.sqrt((ox - self.robot_pos[0])**2 + (oy - self.robot_pos[1])**2)
            if dist < 400: # 400mm = 40cm
                return True
        return False

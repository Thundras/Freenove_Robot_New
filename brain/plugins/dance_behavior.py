"""
Example Plugin: DanceBehavior

This is an example of how to create a custom behavior plugin.
Copy this file as a template for your own plugins.

Usage in YAML:
    behaviors:
      root:
        type: Selector
        children:
          - type: DanceBehavior
            name: HappyDance
            params:
              duration: 5.0
              style: wiggle
"""

import time
import logging
from typing import Dict, Any
from ..bt_core import ParameterLeaf

logger = logging.getLogger(__name__)

PLUGIN_NAME = "DanceBehavior"


class DanceBehavior(ParameterLeaf):
    """
    Makes the robot perform a dance animation.

    Parameters:
        duration: How long to dance (seconds)
        style: Dance style - 'wiggle', 'spin', 'bounce'
    """

    def __init__(self, name: str, context: Dict[str, Any], params: Dict[str, Any]):
        super().__init__(name, context, params)
        self.dance_start_time = 0.0
        self.is_dancing = False

    def run(self) -> bool:
        self._eval_params()

        gait = self.context.get("gait")
        if not gait:
            return False

        style = self.current_params.get("style", "wiggle")
        duration = self.current_params.get("duration", 3.0)

        if not self.is_dancing:
            self.is_dancing = True
            self.dance_start_time = time.time()
            logger.info(f"Starting {style} dance for {duration}s")

        elapsed = time.time() - self.dance_start_time

        if elapsed >= duration:
            gait.set_target_speed(0.0, 0.0)
            gait.set_pose("normal")
            self.is_dancing = False
            return True

        t = elapsed * 3.0

        if style == "wiggle":
            speed = 0.3
            turn = 0.5 * (1 if int(t) % 2 == 0 else -1)
            gait.set_target_speed(speed, turn)

        elif style == "spin":
            gait.set_target_speed(0.2, 1.0)

        elif style == "bounce":
            speed = 0.4
            gait.set_target_speed(speed, 0.0)
            if int(t) % 2 == 0:
                gait.set_pose("sit")
            else:
                gait.set_pose("normal")
        else:
            gait.set_target_speed(0.3, 0.0)

        return True


PLUGIN_CLASS = DanceBehavior

import logging
import time
from flask import Flask, render_template, jsonify, request, Response
from utils.config import ConfigManager

logger = logging.getLogger(__name__)

class WebServer:
    def __init__(self, config: ConfigManager, movement_engine=None, intelligence=None, servo_ctrl=None):
        self.app = Flask(__name__)
        # Silence Flask & Werkzeug access logs completely
        import logging as py_logging
        py_logging.getLogger('werkzeug').setLevel(py_logging.ERROR)
        self.app.logger.disabled = True
        
        self.config = config
        self.movement = movement_engine
        self.intelligence = intelligence
        self.servo_ctrl = servo_ctrl
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/')
        def index():
            # Generate a short unique ID for this run
            instance_id = hex(int(time.time()))[-4:]
            return render_template('index.html', instance_id=instance_id)

        @self.app.route('/api/config', methods=['GET'])
        def get_config():
            return jsonify(self.config._config)

        @self.app.route('/api/config/update', methods=['POST'])
        def update_config():
            data = request.json
            if not data:
                return jsonify({"status": "error", "message": "No data provided"}), 400
            
            for key, value in data.items():
                self.config.set(key, value)
            
            if self.config.save_config():
                logger.info(f"Config updated via Web: {data}")
                return jsonify({"status": "ok"})
            else:
                return jsonify({"status": "error", "message": "Failed to save config"}), 500

        @self.app.route('/api/config/servos', methods=['GET'])
        def get_servo_config():
            return jsonify(self.config.get("servos", {}))

        @self.app.route('/api/config/servos/update', methods=['POST'])
        def update_servo_config():
            data = request.json
            if not data:
                return jsonify({"status": "error", "message": "No data provided"}), 400
            
            # Expecting a dictionary of servo settings
            self.config.set("servos", data)
            
            if self.config.save_config():
                logger.info("Servo configuration updated and saved via API.")
                return jsonify({"status": "ok"})
            else:
                return jsonify({"status": "error", "message": "Failed to save config"}), 500

        @self.app.route('/api/servos', methods=['GET'])
        def get_servos():
            try:
                if self.servo_ctrl:
                    # Return a copy to avoid thread-safety issues during JSON serialization
                    data = dict(self.servo_ctrl.get_servos())
                    return jsonify(data)
                return jsonify({})
            except Exception as e:
                logger.error(f"Error in /api/servos: {e}", exc_info=True)
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route('/api/command/<cmd>', methods=['POST'])
        def handle_command(cmd):
            logger.info(f"Web Command received: {cmd}")
            # Logic to pass to movement engine will go here
            return jsonify({"status": "ok", "command": cmd})

        @self.app.route('/api/gait/<gait>', methods=['POST'])
        def handle_gait(gait):
            logger.info(f"Gait change manual requested: {gait}")
            if self.movement:
                self.movement.change_gait(gait)
            return jsonify({"status": "ok", "gait": gait})

        @self.app.route('/api/pose/<pose>', methods=['POST'])
        def handle_pose(pose):
            logger.debug(f"API Pose request: {pose}")
            if self.movement:
                self.movement.set_pose(pose)
                self.movement.set_target_speed(0.0, 0.0)
            if self.intelligence:
                # Map stationary poses to their respective modes
                if pose in ["sit", "down", "calibrate"]:
                    mode_to_set = pose
                elif pose == "normal":
                    mode_to_set = "autonomous"
                else:
                    mode_to_set = "manual"
                
                self.intelligence.context["system_mode"] = mode_to_set
            return jsonify({"status": "ok", "pose": pose})

        @self.app.route('/api/mode/<mode>', methods=['POST'])
        def handle_mode(mode):
            logger.info(f"!!! API MODE REQUEST: {mode} !!!")
            if self.intelligence:
                self.intelligence.context["system_mode"] = mode
            if self.movement:
                self.movement.set_target_speed(0.0, 0.0)
                if mode == "autonomous":
                    self.movement.set_pose("normal")
            return jsonify({"status": "ok", "mode": mode})

        @self.app.route('/api/height/<float:val>', methods=['POST'])
        def handle_height(val):
            logger.info(f"Body height change requested: {val}mm")
            if self.movement:
                self.movement.set_base_height(val)
                return jsonify({"status": "ok", "height": val})
            return jsonify({"status": "error", "message": "Movement engine not ready"}), 503

        @self.app.route('/api/body/pose', methods=['POST'])
        def handle_body_pose():
            data = request.json
            if not data: return jsonify({"status": "error"}), 400
            if self.movement:
                # Update targets in GaitSequencer
                for k, v in data.items():
                    self.movement.update_body_pose(k, float(v))
                return jsonify({"status": "ok"})
            return jsonify({"status": "error"}), 503

        @self.app.route('/api/servo/test/<motion>', methods=['POST'])
        def handle_servo_test(motion):
            logger.info(f"Servo test motion requested: {motion}")
            if self.movement:
                # Force calibration mode if starting a test motion? 
                # Or just let it run if user is in that tab. 
                # The user said "wenn ich ... auf kalibrierung stelle".
                self.movement.set_test_motion(motion)
                return jsonify({"status": "ok", "motion": motion})
            return jsonify({"status": "error", "message": "Movement engine not ready"}), 503

        @self.app.route('/api/camera_stream')
        def camera_stream():
            def generate():
                while True:
                    try:
                        if self.intelligence and not self.intelligence.frame_queue.empty():
                            # Set a timeout for get() to avoid hanging the generator thread
                            frame = self.intelligence.frame_queue.get(timeout=0.1)
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                        else:
                            time.sleep(0.05)
                    except Exception:
                        # Timeout or empty queue
                        time.sleep(0.05)
            return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
            
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
                
            status = {
                "mode": "autonomous",
                "pose": "normal",
                "gait": "trot",
                "mood": {"energy": 1.0, "excitement": 0.5, "comfort": 0.8},
                "battery": {"voltage": 0.0, "percentage": 0},
                "led": {"pattern": "off", "color": [0,0,0], "pixels": []},
                "buzzer": {"active": False}
            }
                
            if self.intelligence:
                status["mode"] = self.intelligence.context.get("system_mode", "autonomous")
                if "battery" in self.intelligence.context["sensors"]:
                    b_data = self.intelligence.context["sensors"]["battery"].get_data()
                    if b_data:
                        status["battery"] = {"voltage": b_data.voltage, "percentage": b_data.percentage}
                if "led" in self.intelligence.context["sensors"]:
                    led = self.intelligence.context["sensors"]["led"]
                    status["led"] = getattr(led, "current_state", status["led"])
                if "buzzer" in self.intelligence.context["sensors"]:
                    buzzer = self.intelligence.context["sensors"]["buzzer"]
                    status["buzzer"] = {"active": getattr(buzzer, "is_beeping", False)}
                
                if "mood" in self.intelligence.context:
                    status["mood"] = self.intelligence.context["mood"].moods
            
            if self.movement:
                status["pose"] = getattr(self.movement, "current_pose", "normal")
                status["gait"] = getattr(self.movement, "current_gait", "trot")
                
            return jsonify(status)

            return jsonify({"pattern": "off", "color": [0,0,0]})

        @self.app.route('/api/faces', methods=['GET'])
        def get_faces():
            if self.intelligence and hasattr(self.intelligence, "social_memory"):
                return jsonify(self.intelligence.social_memory.faces)
            return jsonify({})

        @self.app.route('/api/faces/rename', methods=['POST'])
        def rename_face():
            data = request.json
            if not data or "id" not in data or "name" not in data:
                return jsonify({"status": "error", "message": "Missing id or name"}), 400
            
            if self.intelligence and hasattr(self.intelligence, "social_memory"):
                success = self.intelligence.social_memory.rename_face(data["id"], data["name"])
                if success:
                    return jsonify({"status": "ok"})
                return jsonify({"status": "error", "message": "Face ID not found"}), 404
            return jsonify({"status": "error", "message": "Intelligence not ready"}), 503
            
        @self.app.route('/api/faces/<fid>', methods=['DELETE'])
        def delete_face(fid):
            if self.intelligence and hasattr(self.intelligence, "social_memory"):
                success = self.intelligence.social_memory.delete_face(fid)
                if success:
                    return jsonify({"status": "ok"})
                return jsonify({"status": "error", "message": "Face ID not found"}), 404
            return jsonify({"status": "error", "message": "Intelligence not ready"}), 503

        @self.app.route('/api/map', methods=['GET'])
        def get_map():
            if self.intelligence and hasattr(self.intelligence, "mapping"):
                m = self.intelligence.mapping
                # Convert tuple keys to strings for JSON serialization
                serializable_grid = {f"{k[0]},{k[1]}": v for k, v in m.grid.items()}
                return jsonify({
                    "robot_pos": m.robot_pos,
                    "robot_yaw": m.robot_yaw,
                    "grid": serializable_grid,
                    "landmarks": m.landmarks
                })
            return jsonify({})

        @self.app.route('/api/markers', methods=['GET'])
        def get_markers():
            return jsonify(self.config.get("mapping.markers", {}))

        @self.app.route('/api/markers', methods=['POST'])
        def update_marker():
            data = request.json
            if not data or "id" not in data or "size" not in data:
                return jsonify({"status": "error", "message": "Missing id or size"}), 400
            
            markers = self.config.get("mapping.markers", {})
            markers[str(data["id"])] = {
                "size": float(data["size"]),
                "name": data.get("name", f"Marker {data['id']}")
            }
            self.config.set("mapping.markers", markers)
            if self.config.save_config():
                return jsonify({"status": "ok"})
            return jsonify({"status": "error", "message": "Failed to save config"}), 500

        @self.app.route('/api/markers/<mid>', methods=['DELETE'])
        def delete_marker(mid):
            markers = self.config.get("mapping.markers", {})
            if str(mid) in markers:
                del markers[str(mid)]
                self.config.set("mapping.markers", markers)
                if self.config.save_config():
                    return jsonify({"status": "ok"})
                return jsonify({"status": "error", "message": "Failed to save config"}), 500
            return jsonify({"status": "error", "message": "Marker not found"}), 404

    def run(self):
        host = self.config.get("system.web_host", "0.0.0.0")
        port = self.config.get("system.web_port", 5000)
        logger.info(f"Starting Web Server on {host}:{port}")
        self.app.run(host=host, port=port, debug=False, use_reloader=False)

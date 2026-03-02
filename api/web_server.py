import logging
import time
from flask import Flask, render_template, jsonify, request, Response
from utils.config import ConfigManager

logger = logging.getLogger(__name__)

class WebServer:
    def __init__(self, config: ConfigManager, movement_engine=None, intelligence=None):
        self.app = Flask(__name__)
        self.config = config
        self.movement = movement_engine
        self.intelligence = intelligence
        print(f"DIAG: Web Server Context ID: {id(self.intelligence.context) if self.intelligence else 'N/A'}")
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

        @self.app.route('/api/command/<cmd>', methods=['POST'])
        def handle_command(cmd):
            logger.info(f"Web Command received: {cmd}")
            # Logic to pass to movement engine will go here
            return jsonify({"status": "ok", "command": cmd})

        @self.app.route('/api/gait/<gait>', methods=['POST'])
        def handle_gait(gait):
            logger.info(f"Gait change requested: {gait}")
            if self.movement:
                self.movement.set_gait(gait)
            return jsonify({"status": "ok", "gait": gait})

        @self.app.route('/api/pose/<pose>', methods=['POST'])
        def handle_pose(pose):
            # Critical log to verify receiving request
            print(f"DEBUG: !!! API POSE REQUEST RECEIVED: {pose} !!!")
            logger.info(f"!!! API POSE REQUEST: {pose} !!!")
            if self.movement:
                self.movement.set_pose(pose)
                self.movement.set_target_speed(0.0, 0.0)
            if self.intelligence:
                # Map stationary poses to their respective modes
                if pose in ["sit", "down"]:
                    mode_to_set = pose
                elif pose == "normal":
                    mode_to_set = "autonomous"
                else:
                    mode_to_set = "manual"
                
                logger.info(f"API Mapping: Pose {pose} -> Mode {mode_to_set}")
                self.intelligence.context["system_mode"] = mode_to_set
                # Double check the assigned value
                logger.info(f"Verified Context Mode: {self.intelligence.context['system_mode']}")
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
            # Throttle debug print to avoid flooding, but keep it consistent
            if int(time.time()) % 10 == 0:
                print(f"DEBUG: Status API called from {request.remote_addr}")
                
            status = {
                "mode": "autonomous",
                "pose": "normal",
                "gait": "trot",
                "battery": {"voltage": 0.0, "percentage": 0},
                "led": {"pattern": "off", "color": [0,0,0], "pixels": []}
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

    def run(self):
        host = self.config.get("system.web_host", "0.0.0.0")
        port = self.config.get("system.web_port", 5000)
        logger.info(f"Starting Web Server on {host}:{port}")
        self.app.run(host=host, port=port, debug=False, use_reloader=False)

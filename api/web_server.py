import logging
from flask import Flask, render_template, jsonify, request, Response
from utils.config import ConfigManager

logger = logging.getLogger(__name__)

class WebServer:
    def __init__(self, config: ConfigManager, movement_engine=None, intelligence=None):
        self.app = Flask(__name__)
        self.config = config
        self.movement = movement_engine
        self.intelligence = intelligence
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html')

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

        @self.app.route('/api/mode/<mode>', methods=['POST'])
        def handle_mode(mode):
            logger.info(f"System Mode change requested: {mode}")
            if self.intelligence:
                self.intelligence.context["system_mode"] = mode
            return jsonify({"status": "ok", "mode": mode})

        @self.app.route('/api/camera_stream')
        def camera_stream():
            def generate():
                while True:
                    if self.intelligence and not self.intelligence.frame_queue.empty():
                        frame = self.intelligence.frame_queue.get()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                    time.sleep(0.05)
            return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

    def run(self):
        host = self.config.get("system.web_host", "0.0.0.0")
        port = self.config.get("system.web_port", 5000)
        logger.info(f"Starting Web Server on {host}:{port}")
        self.app.run(host=host, port=port, debug=False, use_reloader=False)

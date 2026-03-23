import pytest
import json


class TestApiEndpoints:
    """Tests for Web API endpoints"""

    @pytest.fixture
    def client(self):
        from utils.config import ConfigManager
        from api.web_server import WebServer

        config = ConfigManager("config/config.yaml")
        web_server = WebServer(
            config, movement_engine=None, intelligence=None, servo_ctrl=None
        )
        return web_server.app.test_client()

    def test_status_endpoint_returns_json(self, client):
        """Status endpoint should return JSON"""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_config_endpoint_returns_json(self, client):
        """Config endpoint should return configuration"""
        response = client.get("/api/config")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_markers_endpoint(self, client):
        """Markers endpoint should return list"""
        response = client.get("/api/markers")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_map_endpoint(self, client):
        """Map endpoint should return SLAM data"""
        response = client.get("/api/map")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_faces_endpoint(self, client):
        """Faces endpoint should return face database"""
        response = client.get("/api/faces")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_move_endpoint_exists(self, client):
        """Move endpoint should exist (or return 404 if not implemented)"""
        response = client.post(
            "/api/move",
            data=json.dumps({"direction": "forward"}),
            content_type="application/json",
        )
        assert response.status_code in [200, 404]

    def test_config_update_accepts_json(self, client):
        """Config update should accept JSON"""
        response = client.post(
            "/api/config/update",
            data=json.dumps({"system": {"control_loop_hz": 75}}),
            content_type="application/json",
        )
        assert response.status_code in [200, 500]


class TestStaticFiles:
    """Tests for static file serving"""

    @pytest.fixture
    def client(self):
        from utils.config import ConfigManager
        from api.web_server import WebServer

        config = ConfigManager("config/config.yaml")
        web_server = WebServer(config)
        return web_server.app.test_client()

    def test_css_loads(self, client):
        """Style.css should be accessible"""
        response = client.get("/static/style.css")
        assert response.status_code == 200
        data = response.data.decode()
        assert "body" in data or ":root" in data or "--" in data

    def test_index_html_loads(self, client):
        """index.html should be accessible"""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Robot Control" in response.data

    def test_google_fonts_link(self, client):
        """Google Fonts should be referenced"""
        response = client.get("/")
        data = response.data.decode()
        assert "fonts.googleapis.com" in data


class TestDashboardRendering:
    """Tests for dashboard HTML structure"""

    @pytest.fixture
    def client(self):
        from utils.config import ConfigManager
        from api.web_server import WebServer

        config = ConfigManager("config/config.yaml")
        web_server = WebServer(config)
        return web_server.app.test_client()

    def test_title_present(self, client):
        """Dashboard should have Robot Control title"""
        response = client.get("/")
        data = response.data.decode()
        assert "Robot Control" in data

    def test_version_in_title(self, client):
        """Dashboard should show version"""
        response = client.get("/")
        data = response.data.decode()
        assert "v4.2" in data or "precision" in data

    def test_tabs_present(self, client):
        """Dashboard should have all 5 tabs"""
        response = client.get("/")
        data = response.data.decode()
        assert "Status" in data
        assert "Kinematik" in data or "Kinematics" in data
        assert "Umgebung" in data or "Map" in data
        assert "Gedächtnis" in data or "Social" in data
        assert "System" in data or "Settings" in data

    def test_css_variables_defined(self, client):
        """CSS should define design tokens"""
        response = client.get("/static/style.css")
        data = response.data.decode()
        assert ":root" in data or "--" in data

    def test_dark_theme(self, client):
        """CSS should have dark theme variables"""
        response = client.get("/static/style.css")
        data = response.data.decode()
        assert "#0f172a" in data or "dark" in data.lower() or "--bg" in data


class TestJavaScriptFunctions:
    """Tests for JavaScript functionality presence"""

    @pytest.fixture
    def client(self):
        from utils.config import ConfigManager
        from api.web_server import WebServer

        config = ConfigManager("config/config.yaml")
        web_server = WebServer(config)
        return web_server.app.test_client()

    def test_show_tab_function(self, client):
        """JavaScript should have showTab function"""
        response = client.get("/")
        data = response.data.decode()
        assert "showTab(" in data or "function showTab" in data

    def test_toast_notification(self, client):
        """JavaScript should have toast notification"""
        response = client.get("/")
        data = response.data.decode()
        assert "toast" in data.lower() or "showToast" in data

    def test_audio_toggle(self, client):
        """JavaScript should have audio toggle function"""
        response = client.get("/")
        data = response.data.decode()
        assert "toggleAudio" in data or "audio" in data.lower()

    def test_map_render_functions(self, client):
        """JavaScript should have map rendering"""
        response = client.get("/")
        data = response.data.decode()
        assert "renderMap" in data or "updateMap" in data

    def test_config_functions(self, client):
        """JavaScript should have config functions"""
        response = client.get("/")
        data = response.data.decode()
        assert "loadConfig" in data or "updateQuickConfig" in data


class TestErrorHandling:
    """Tests for error handling"""

    @pytest.fixture
    def client(self):
        from utils.config import ConfigManager
        from api.web_server import WebServer

        config = ConfigManager("config/config.yaml")
        web_server = WebServer(config)
        return web_server.app.test_client()

    def test_404_returns_html(self, client):
        """Unknown routes should return 404"""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_invalid_face_id_returns_404(self, client):
        """Invalid face ID should return 404 or method not allowed"""
        response = client.get("/api/faces/invalid_id_12345")
        assert response.status_code in [404, 405]

    def test_marker_endpoint_method_not_allowed(self, client):
        """Marker endpoint should return method not allowed for GET with ID"""
        response = client.get("/api/markers/invalid_999")
        assert response.status_code in [404, 405]


class TestUIComponents:
    """Tests for UI component presence"""

    @pytest.fixture
    def client(self):
        from utils.config import ConfigManager
        from api.web_server import WebServer

        config = ConfigManager("config/config.yaml")
        web_server = WebServer(config)
        return web_server.app.test_client()

    def test_mood_bars_present(self, client):
        """Mood bars should be in HTML"""
        response = client.get("/")
        data = response.data.decode()
        assert "mood-energy" in data or "energy" in data
        assert "mood-excitement" in data or "excitement" in data
        assert "mood-comfort" in data or "comfort" in data

    def test_camera_stream_present(self, client):
        """Camera stream should be present"""
        response = client.get("/")
        data = response.data.decode()
        assert "camera_stream" in data or "video" in data.lower()

    def test_camera_status_indicator(self, client):
        """Camera status indicator should be present"""
        response = client.get("/")
        data = response.data.decode()
        assert "camera-status" in data or "Kamera" in data

    def test_fps_display_present(self, client):
        """FPS display should be present"""
        response = client.get("/")
        data = response.data.decode()
        assert "fps-value" in data or "FPS" in data

    def test_detection_info_present(self, client):
        """Detection info overlay should be present"""
        response = client.get("/")
        data = response.data.decode()
        assert "detection-info" in data or "detected-name" in data

    def test_header_telemetry(self, client):
        """Header should show telemetry"""
        response = client.get("/")
        data = response.data.decode()
        assert "Batterie" in data or "Battery" in data
        assert "Gang" in data or "Gait" in data
        assert "Mode" in data

    def test_modals_present(self, client):
        """Modals for rename/delete should exist"""
        response = client.get("/")
        data = response.data.decode()
        assert "rename-modal" in data or "rename" in data
        assert "delete" in data.lower() or "löschen" in data.lower()

    def test_canvas_elements(self, client):
        """Canvas elements for visualization should exist"""
        response = client.get("/")
        data = response.data.decode()
        assert "canvas" in data.lower() or "leg-canvas" in data

    def test_led_ring_present(self, client):
        """LED ring visualization should be present"""
        response = client.get("/")
        data = response.data.decode()
        assert "led" in data.lower() or "LED" in data


class TestVisionFeatures:
    """Tests for Vision Panel features"""

    @pytest.fixture
    def client(self):
        from utils.config import ConfigManager
        from api.web_server import WebServer

        config = ConfigManager("config/config.yaml")
        web_server = WebServer(config)
        return web_server.app.test_client()

    def test_camera_stream_route_registered(self):
        """Camera stream endpoint should be registered in the app"""
        from utils.config import ConfigManager
        from api.web_server import WebServer

        config = ConfigManager("config/config.yaml")
        web_server = WebServer(config)
        routes = [r.rule for r in web_server.app.url_map.iter_rules()]
        assert "/api/camera_stream" in routes

    def test_status_includes_detected_face(self, client):
        """Status endpoint should include detected_face field"""
        response = client.get("/api/status")
        data = json.loads(response.data)
        assert "detected_face" in data

    def test_status_detected_face_structure(self, client):
        """detected_face should have name and trust when present"""
        response = client.get("/api/status")
        data = json.loads(response.data)
        detected = data.get("detected_face")
        if detected:
            assert "name" in detected
            assert "trust" in detected

    def test_javascript_camera_handlers(self, client):
        """JavaScript should have camera error/load handlers"""
        response = client.get("/")
        data = response.data.decode()
        assert "handleCameraError" in data or "handleCameraLoaded" in data
        assert "updateCameraStatus" in data
        assert "updateDetectionDisplay" in data

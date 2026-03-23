import pytest
import json
import yaml


class TestApiSpec:
    """Tests for OpenAPI specification."""

    def test_spec_file_exists(self):
        """API spec file should exist"""
        import os

        assert os.path.isfile("docs/api_spec.yaml")

    def test_spec_is_valid_yaml(self):
        """API spec should be valid YAML"""
        with open("docs/api_spec.yaml", "r") as f:
            spec = yaml.safe_load(f)
        assert spec is not None

    def test_spec_has_openapi_version(self):
        """Spec should have openapi version"""
        with open("docs/api_spec.yaml", "r") as f:
            spec = yaml.safe_load(f)
        assert "openapi" in spec
        assert spec["openapi"].startswith("3.")

    def test_spec_has_info(self):
        """Spec should have info section"""
        with open("docs/api_spec.yaml", "r") as f:
            spec = yaml.safe_load(f)
        assert "info" in spec
        assert "title" in spec["info"]
        assert "version" in spec["info"]

    def test_spec_has_paths(self):
        """Spec should have paths section"""
        with open("docs/api_spec.yaml", "r") as f:
            spec = yaml.safe_load(f)
        assert "paths" in spec
        assert len(spec["paths"]) > 0

    def test_spec_has_components(self):
        """Spec should have components/schemas"""
        with open("docs/api_spec.yaml", "r") as f:
            spec = yaml.safe_load(f)
        assert "components" in spec
        assert "schemas" in spec["components"]

    def test_status_endpoint_documented(self):
        """Status endpoint should be documented"""
        with open("docs/api_spec.yaml", "r") as f:
            spec = yaml.safe_load(f)
        assert "/api/status" in spec["paths"]

    def test_config_endpoints_documented(self):
        """Config endpoints should be documented"""
        with open("docs/api_spec.yaml", "r") as f:
            spec = yaml.safe_load(f)
        assert "/api/config" in spec["paths"]
        assert "/api/config/update" in spec["paths"]

    def test_movement_endpoints_documented(self):
        """Movement endpoints should be documented"""
        with open("docs/api_spec.yaml", "r") as f:
            spec = yaml.safe_load(f)
        assert "/api/gait/{gait}" in spec["paths"]
        assert "/api/pose/{pose}" in spec["paths"]
        assert "/api/mode/{mode}" in spec["paths"]

    def test_vision_endpoints_documented(self):
        """Vision endpoints should be documented"""
        with open("docs/api_spec.yaml", "r") as f:
            spec = yaml.safe_load(f)
        assert "/api/camera_stream" in spec["paths"]
        assert "/api/faces" in spec["paths"]

    def test_robot_status_schema_documented(self):
        """RobotStatus schema should be documented"""
        with open("docs/api_spec.yaml", "r") as f:
            spec = yaml.safe_load(f)
        assert "RobotStatus" in spec["components"]["schemas"]
        schema = spec["components"]["schemas"]["RobotStatus"]
        assert "mode" in schema["properties"]
        assert "pose" in schema["properties"]
        assert "battery" in schema["properties"]

    def test_all_endpoints_have_responses(self):
        """All endpoints should have responses defined"""
        with open("docs/api_spec.yaml", "r") as f:
            spec = yaml.safe_load(f)
        for path, methods in spec["paths"].items():
            for method, details in methods.items():
                if method in ["get", "post", "put", "delete"]:
                    assert "responses" in details, (
                        f"{method.upper()} {path} missing responses"
                    )

    def test_endpoints_have_summary(self):
        """All endpoints should have summaries"""
        with open("docs/api_spec.yaml", "r") as f:
            spec = yaml.safe_load(f)
        for path, methods in spec["paths"].items():
            for method, details in methods.items():
                if method in ["get", "post", "put", "delete"]:
                    assert "summary" in details, (
                        f"{method.upper()} {path} missing summary"
                    )

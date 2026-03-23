import pytest
import os


class TestSystemdServiceFile:
    """Tests for systemd service file."""

    def test_service_file_exists(self):
        """Service file should exist"""
        service_path = os.path.join(
            os.path.dirname(__file__), "..", "deploy", "freenove_dog.service"
        )
        assert os.path.isfile(service_path)

    def test_service_has_unit_section(self):
        """Service file should have [Unit] section"""
        with open("deploy/freenove_dog.service", "r") as f:
            content = f.read()
        assert "[Unit]" in content

    def test_service_has_service_section(self):
        """Service file should have [Service] section"""
        with open("deploy/freenove_dog.service", "r") as f:
            content = f.read()
        assert "[Service]" in content

    def test_service_has_install_section(self):
        """Service file should have [Install] section"""
        with open("deploy/freenove_dog.service", "r") as f:
            content = f.read()
        assert "[Install]" in content

    def test_service_has_description(self):
        """Service should have Description"""
        with open("deploy/freenove_dog.service", "r") as f:
            content = f.read()
        assert "Description=" in content

    def test_service_has_execstart(self):
        """Service should have ExecStart"""
        with open("deploy/freenove_dog.service", "r") as f:
            content = f.read()
        assert "ExecStart=" in content

    def test_service_has_restart_policy(self):
        """Service should have Restart policy"""
        with open("deploy/freenove_dog.service", "r") as f:
            content = f.read()
        assert "Restart=on-failure" in content

    def test_service_has_user(self):
        """Service should specify User"""
        with open("deploy/freenove_dog.service", "r") as f:
            content = f.read()
        assert "User=pi" in content

    def test_service_has_graceful_shutdown(self):
        """Service should have ExecStop for graceful shutdown"""
        with open("deploy/freenove_dog.service", "r") as f:
            content = f.read()
        assert "ExecStop=" in content


class TestSetupScript:
    """Tests for setup script."""

    def test_setup_script_exists(self):
        """Setup script should exist"""
        script_path = os.path.join(
            os.path.dirname(__file__), "..", "deploy", "setup_service.sh"
        )
        assert os.path.isfile(script_path)

    def test_setup_script_is_executable_format(self):
        """Setup script should have shebang"""
        with open("deploy/setup_service.sh", "r") as f:
            first_line = f.readline()
        assert first_line.startswith("#!/bin/bash")

"""Deployment configuration: health, DATA_DIR, PORT, app bootstrap."""

import runtime_config


class TestRuntimeConfig:
    def test_data_dir_default(self, monkeypatch):
        from pathlib import Path

        monkeypatch.delenv("DATA_DIR", raising=False)
        assert runtime_config.get_data_dir() == Path(
            runtime_config.DEFAULT_DATA_DIR
        )

    def test_data_dir_override(self, monkeypatch):
        monkeypatch.setenv("DATA_DIR", "/var/ftp-data")
        from pathlib import Path

        assert runtime_config.get_data_dir() == Path("/var/ftp-data")

    def test_port_default(self, monkeypatch):
        monkeypatch.delenv("PORT", raising=False)
        assert runtime_config.get_port() == 5000

    def test_port_override(self, monkeypatch):
        monkeypatch.setenv("PORT", "8080")
        assert runtime_config.get_port() == 8080

    def test_tesseract_cmd_env(self, monkeypatch):
        monkeypatch.setenv("TESSERACT_CMD", "/usr/bin/tesseract")
        assert runtime_config.resolve_tesseract_cmd() == "/usr/bin/tesseract"


class TestDeploymentHttp:
    def test_health_returns_ok(self):
        import interface_server as server

        client = server.app.test_client()
        response = client.get("/health")
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}

    def test_flask_app_initialises(self):
        import interface_server as server

        assert server.app is not None
        assert server.BASE_DIR is not None
        assert server.PORT == runtime_config.get_port()

    def test_home_route_still_serves(self):
        import interface_server as server

        response = server.app.test_client().get("/")
        assert response.status_code == 200
        assert b"Freeing the Parrot" in response.data
        assert b'id="s1"' in response.data

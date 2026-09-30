"""FTP 2.0 participant shell markup and static assets (contract guards)."""

from pathlib import Path

import interface_server as server


class TestFtp2Shell:
    def test_home_includes_core_shell_ids(self):
        client = server.app.test_client()
        html = client.get("/").get_data(as_text=True)
        assert 'id="camera-overlay"' in html
        assert "ftp2-camera-overlay" in html
        assert "hidden" in html.split('id="camera-overlay"')[1][:80]
        assert 'id="entry-error"' in html
        assert 'id="screen-entry"' in html
        assert 'id="screen-conversation"' in html
        assert 'id="screen-deck"' in html
        assert 'id="screen-reveal"' in html
        assert 'id="deck-grid"' in html
        assert 'id="trace-list"' in html

    def test_home_preserves_api_hook_ids(self):
        client = server.app.test_client()
        html = client.get("/").get_data(as_text=True)
        for element_id in (
            "btn-enter",
            "btn-send",
            "btn-voice",
            "btn-image",
            "btn-camera",
            "message-input",
            "image-file-input",
            "camera-preview",
        ):
            assert 'id="' + element_id + '"' in html

    def test_ftp2_css_respects_hidden_on_camera_overlay(self):
        css = Path(__file__).resolve().parents[1] / "static" / "ftp2.css"
        text = css.read_text(encoding="utf-8")
        assert ".ftp2-camera-overlay[hidden]" in text
        assert "display: none !important" in text.split(".ftp2-camera-overlay[hidden]")[1][:80]

    def test_ftp2_css_design_tokens_present(self):
        css = Path(__file__).resolve().parents[1] / "static" / "ftp2.css"
        text = css.read_text(encoding="utf-8")
        assert "#07110d" in text.lower() or "#07110D" in text
        assert "--ftp2-paper" in text

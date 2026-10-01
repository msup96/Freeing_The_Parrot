"""FTP 2.0 participant shell markup and static assets (contract guards)."""

from pathlib import Path

import interface_server as server


class TestFtp2Shell:
    def test_home_includes_core_shell_ids(self):
        client = server.app.test_client()
        html = client.get("/").get_data(as_text=True)
        for screen_id in ("s1", "s2", "s3", "s4", "s6", "s7", "s8", "s9"):
            assert 'id="' + screen_id + '"' in html
        for element_id in ("ap", "slots", "go3", "par", "log", "vit", "dt", "tiles", "mark"):
            assert 'id="' + element_id + '"' in html

    def test_home_preserves_api_hook_ids(self):
        client = server.app.test_client()
        html = client.get("/").get_data(as_text=True)
        for element_id in ("enter", "send", "say", "done", "private", "wall", "flow-error"):
            assert 'id="' + element_id + '"' in html

    def test_ftp2_css_preserves_reference_motion_and_registration_marks(self):
        css = Path(__file__).resolve().parents[1] / "static" / "ftp2.css"
        text = css.read_text(encoding="utf-8")
        assert ".reg.a" in text
        assert "@media(prefers-reduced-motion:reduce)" in text

    def test_ftp2_css_design_tokens_present(self):
        css = Path(__file__).resolve().parents[1] / "static" / "ftp2.css"
        text = css.read_text(encoding="utf-8")
        assert "#07110d" in text.lower() or "#07110D" in text
        assert "--paper:#E6D7B8" in text
        assert "--gold:#C4A035" in text

    def test_parrot_presence_uses_behavior_map_and_unlabeled_trace(self):
        root = Path(__file__).resolve().parents[1]
        html = server.app.test_client().get("/").get_data(as_text=True)
        script = (root / "static" / "ftp2.js").read_text(encoding="utf-8")
        for behavior in (
            "understanding",
            "mirroring",
            "absurd",
            "memory_loss",
            "roast",
            "system_glitch",
            "help_me",
            "mixed",
            "banana",
        ):
            assert behavior + ": [" in script
        assert 'aria-label="Observation trace"' in html
        assert 'data-mark="turns"' in html
        assert 'data-mark="pauses"' in html
        assert 'data-mark="questions"' in html
        assert 'data-mark="repeats"' in html
        assert "result.roast_level" not in script

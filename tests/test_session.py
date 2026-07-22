"""Tests for session management: Session, HttpClient, save_cookies.

Seams:
  - Session.load() -> Session
  - Session.http() -> HttpClient
  - HttpClient.get(url) -> dict
  - HttpClient.post(url, data) -> dict
  - Session.mid property
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from bilibili_fav_classifier.session import HttpClient, Session


# ── Session.load ──────────────────────────────────────────────────

class TestSessionLoad:
    def test_loads_cookies_from_disk(self, tmp_path, monkeypatch):
        """Session.load reads cookies.json and extracts csrf."""
        import bilibili_fav_classifier.session as session_mod

        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(
            json.dumps([
                {"name": "bili_jct", "value": "csrf_token_123"},
                {"name": "SESSDATA", "value": "sess_abc"},
            ], ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(session_mod, "COOKIES_PATH", cookie_file)

        session = Session.load()
        assert session.csrf == "csrf_token_123"
        assert session.cookies == {"bili_jct": "csrf_token_123", "SESSDATA": "sess_abc"}

    def test_raises_without_csrf(self, tmp_path, monkeypatch):
        """Session.load raises ValueError when bili_jct is missing."""
        import bilibili_fav_classifier.session as session_mod

        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(
            json.dumps([{"name": "SESSDATA", "value": "sess_abc"}], ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(session_mod, "COOKIES_PATH", cookie_file)

        with pytest.raises(ValueError, match="bili_jct"):
            Session.load()

    def test_mid_proxy_for_user_mid(self, tmp_path, monkeypatch):
        """Session.mid returns USER_MID from config."""
        import bilibili_fav_classifier.session as session_mod
        import bilibili_fav_classifier.config as config_mod

        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(
            json.dumps([{"name": "bili_jct", "value": "test"}], ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(session_mod, "COOKIES_PATH", cookie_file)
        # Patch USER_MID at session module level (where mid property reads it)
        monkeypatch.setattr(session_mod, "USER_MID", "99999999")

        session = Session.load()
        assert session.mid == "99999999"


# ── Session.http() ────────────────────────────────────────────────

class TestSessionHttp:
    def test_returns_http_client(self):
        """Session.http() returns an HttpClient with the session's cookies."""
        session = Session(cookies={"bili_jct": "test"}, csrf="test")
        http = session.http()
        assert isinstance(http, HttpClient)
        assert http.cookies == {"bili_jct": "test"}

    def test_http_client_has_default_headers(self):
        """HttpClient has default Bilibili headers."""
        session = Session(cookies={"bili_jct": "test"}, csrf="test")
        http = session.http()
        assert "Referer" in http.headers
        assert "User-Agent" in http.headers

    def test_http_client_custom_headers(self):
        """HttpClient accepts custom headers (replaces defaults)."""
        http = HttpClient(cookies={}, headers={"X-Custom": "value"})
        assert http.headers["X-Custom"] == "value"
        # Custom headers replace defaults entirely
        assert "Referer" not in http.headers


# ── HttpClient (injectable seam) ──────────────────────────────────

class TestHttpClient:
    def test_get_returns_json(self, monkeypatch):
        """HttpClient.get returns parsed JSON."""
        captured = {}

        def mock_get(url, **kwargs):
            captured["url"] = url
            captured["cookies"] = kwargs.get("cookies")
            return type("Response", (), {"json": lambda self: {"code": 0, "data": "ok"}})()

        monkeypatch.setattr("requests.get", mock_get)
        http = HttpClient(cookies={"test": "val"})
        result = http.get("https://api.example.com/test")
        assert result == {"code": 0, "data": "ok"}
        assert captured["cookies"] == {"test": "val"}

    def test_post_returns_json(self, monkeypatch):
        """HttpClient.post returns parsed JSON."""
        captured = {}

        class FakeResponse:
            headers = {"content-type": "application/json"}
            def json(self):
                return {"code": 0}

        def mock_post(url, **kwargs):
            captured["url"] = url
            captured["data"] = kwargs.get("data")
            return FakeResponse()

        monkeypatch.setattr("requests.post", mock_post)
        http = HttpClient(cookies={"test": "val"})
        result = http.post("https://api.example.com/post", {"key": "value"})
        assert result == {"code": 0}
        assert captured["data"] == {"key": "value"}

    def test_post_handles_non_json_response(self, monkeypatch):
        """HttpClient.post returns WAF error dict for HTML responses."""
        class FakeResponse:
            headers = {"content-type": "text/html"}
            status_code = 503

        def mock_post(url, **kwargs):
            return FakeResponse()

        monkeypatch.setattr("requests.post", mock_post)
        http = HttpClient(cookies={})
        result = http.post("https://api.example.com/post", {})
        assert result.get("_waf_html") is True
        assert result.get("_status") == 503

    def test_post_handles_timeout(self, monkeypatch):
        """HttpClient.post returns error dict on exception."""
        def mock_post(url, **kwargs):
            raise TimeoutError("connection timeout")

        monkeypatch.setattr("requests.post", mock_post)
        http = HttpClient(cookies={})
        result = http.post("https://api.example.com/post", {})
        assert "_error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

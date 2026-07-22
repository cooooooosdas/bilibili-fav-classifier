"""Tests for apply.py with injectable HttpClient.

Seams:
  - apply(http: HttpClient, csrf: str, only_folder: str | None) -> None
  - _batch_move(http, csrf, src, tar, resources) -> dict
  - _resolve_default(http) -> (str, int)
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from bilibili_fav_classifier.apply import apply, _batch_move, _load_folders


# ── Helpers ──────────────────────────────────────────────────────

class FakeHttp:
    """Injectable fake HTTP client for testing apply logic."""

    def __init__(self, responses: dict[str, dict]):
        self.responses = responses
        self.calls: list[dict] = []

    def get(self, url: str) -> dict:
        self.calls.append({"method": "get", "url": url})
        return self.responses.get(url, {})

    def post(self, url: str, data: dict) -> dict:
        self.calls.append({"method": "post", "url": url, "data": data})
        return self.responses.get(url, {"code": 0})


def _setup_test_env(tmp_path, monkeypatch, plan_groups: dict, cookie_file=None) -> Path:
    """Set up config paths and write plan.json for apply tests.

    Returns the path to the written plan.json for passing to apply().
    """
    import bilibili_fav_classifier.config as config_mod

    if cookie_file is None:
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(
            json.dumps([{"name": "bili_jct", "value": "csrf_test"}], ensure_ascii=False),
            encoding="utf-8",
        )
    monkeypatch.setattr(config_mod, "COOKIES_PATH", cookie_file)

    plan_file = tmp_path / "plan.json"
    plan = {"move": True, "groups": plan_groups}
    plan_file.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    return plan_file


# ── _resolve_default ─────────────────────────────────────────────

class TestLoadFolders:
    def test_returns_default_folder(self):
        http = FakeHttp({
            "https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid=&platform=web": {
                "data": {"list": [
                    {"title": "默认收藏夹", "id": 12345},
                    {"title": "其他", "id": 99999},
                ]}
            },
        })
        name_to_id, default_id = _load_folders(http)
        assert "默认收藏夹" in name_to_id
        assert name_to_id["默认收藏夹"] == 12345
        assert default_id == 12345

    def test_falls_back_to_config_when_not_found(self):
        http = FakeHttp({
            "https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid=&platform=web": {
                "data": {"list": []}
            },
        })
        name_to_id, default_id = _load_folders(http)
        assert name_to_id == {}
        assert default_id == 0


# ── _batch_move ──────────────────────────────────────────────────

class TestBatchMove:
    def test_builds_correct_request(self):
        """_batch_move sends correct resources format."""
        http = FakeHttp({
            "https://api.bilibili.com/x/v3/fav/resource/move": {"code": 0},
        })
        result = _batch_move(http, "csrf123", 100, 200, ["BV1abc", "BV2def"])
        assert result["code"] == 0
        post_calls = [c for c in http.calls if c["method"] == "post"]
        assert len(post_calls) == 1
        data = post_calls[0]["data"]
        assert data["src_media_id"] == "100"
        assert data["tar_media_id"] == "200"
        assert data["csrf"] == "csrf123"
        assert data["mid"] == ""
        assert data["platform"] == "web"
        assert data["resources"] == "BV1abc:2,BV2def:2"

    def test_empty_resources(self):
        """_batch_move handles empty resource list."""
        http = FakeHttp({
            "https://api.bilibili.com/x/v3/fav/resource/move": {"code": 0},
        })
        result = _batch_move(http, "csrf", 1, 2, [])
        assert result["code"] == 0
        data = [c for c in http.calls if c["method"] == "post"][0]["data"]
        assert data["resources"] == ""


# ── apply() integration tests ─────────────────────────────────────

class TestApply:
    def test_skips_other_folder(self, tmp_path, monkeypatch, capsys):
        """Videos in '其他' folder are skipped."""
        plan_file = _setup_test_env(tmp_path, monkeypatch, {
            "其他": [{"id": 1, "bvid": "BV1"}],
            "AI与编程技术": [{"id": 2, "bvid": "BV2"}],
        })
        http = FakeHttp({
            "https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid=&platform=web": {
                "data": {"list": []}
            },
            "https://api.bilibili.com/x/v3/fav/folder/add": {"code": 0, "data": {"id": 1}},
            "https://api.bilibili.com/x/v3/fav/resource/move": {"code": 0},
        })
        apply(http, "csrf_test", plan_path=plan_file)
        captured = capsys.readouterr().out
        assert "跳过 '其他'" in captured

    def test_creates_missing_folder(self, tmp_path, monkeypatch, capsys):
        """apply creates a folder that doesn't exist yet."""
        plan_file = _setup_test_env(tmp_path, monkeypatch, {
            "AI与编程技术": [{"id": 1, "bvid": "BV1"}],
        })
        http = FakeHttp({
            "https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid=&platform=web": {
                "data": {"list": []}
            },
            "https://api.bilibili.com/x/v3/fav/folder/add": {"code": 0, "data": {"id": 55555}},
            "https://api.bilibili.com/x/v3/fav/resource/move": {"code": 0},
        })
        apply(http, "csrf_test", plan_path=plan_file)
        captured = capsys.readouterr().out
        assert "创建收藏夹: AI与编程技术" in captured
        assert "创建成功 id=55555" in captured

    def test_reuses_existing_folder(self, tmp_path, monkeypatch, capsys):
        """apply skips creation when folder already exists."""
        plan_file = _setup_test_env(tmp_path, monkeypatch, {
            "AI与编程技术": [{"id": 1, "bvid": "BV1"}],
        })
        http = FakeHttp({
            "https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid=&platform=web": {
                "data": {"list": [{"title": "AI与编程技术", "id": 77777}]}
            },
            "https://api.bilibili.com/x/v3/fav/resource/move": {"code": 0},
        })
        apply(http, "csrf_test", plan_path=plan_file)
        captured = capsys.readouterr().out
        assert "收藏夹已存在" in captured
        post_calls = [c for c in http.calls if c["method"] == "post"]
        assert not any("folder/add" in c["url"] for c in post_calls)

    def test_only_folder_filter(self, tmp_path, monkeypatch, capsys):
        """apply only_folder param skips non-matching folders."""
        plan_file = _setup_test_env(tmp_path, monkeypatch, {
            "音乐": [{"id": 1, "bvid": "BV1"}],
            "游戏与动漫": [{"id": 2, "bvid": "BV2"}],
        })
        http = FakeHttp({
            "https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid=&platform=web": {
                "data": {"list": []}
            },
            "https://api.bilibili.com/x/v3/fav/folder/add": {"code": 0, "data": {"id": 1}},
            "https://api.bilibili.com/x/v3/fav/resource/move": {"code": 0},
        })
        apply(http, "csrf_test", only_folder="音乐", plan_path=plan_file)
        captured = capsys.readouterr().out
        assert "音乐" in captured
        assert "游戏与动漫" not in captured

    def test_writes_apply_log(self, tmp_path, monkeypatch):
        """apply writes apply_log.json with results."""
        plan_file = _setup_test_env(tmp_path, monkeypatch, {
            "AI与编程技术": [{"id": 1, "bvid": "BV1"}],
        })
        log_file = tmp_path / "apply_log.json"

        http = FakeHttp({
            "https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid=&platform=web": {
                "data": {"list": []}
            },
            "https://api.bilibili.com/x/v3/fav/folder/add": {"code": 0, "data": {"id": 111}},
            "https://api.bilibili.com/x/v3/fav/resource/move": {"code": 0},
        })
        apply(http, "csrf_test", plan_path=plan_file, log_path=log_file)

        log = json.loads(log_file.read_text(encoding="utf-8"))
        assert len(log) == 1
        assert log[0]["folder"] == "AI与编程技术"
        assert log[0]["moved"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

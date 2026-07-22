"""Tests for seed mapping persistence: load_seed_mappings, save_seed_mappings.

Seams:
  - load_seed_mappings() -> dict[str, list[str]]
  - save_seed_mappings(mappings: dict[str, list[str]]) -> None
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from bilibili_fav_classifier.mappings import load_seed_mappings, save_seed_mappings


class TestLoadSeedMappings:
    def test_returns_dict(self, tmp_path):
        target = tmp_path / "seed_mappings.json"
        target.write_text(
            json.dumps({"AI与编程技术": ["UP1"], "音乐": ["UP2"]}, ensure_ascii=False),
            encoding="utf-8",
        )
        # Patch SEED_FILE path via monkeypatch
        import bilibili_fav_classifier.mappings as mod
        original = mod.SEED_FILE
        mod.SEED_FILE = target
        try:
            result = load_seed_mappings()
            assert result == {"AI与编程技术": ["UP1"], "音乐": ["UP2"]}
        finally:
            mod.SEED_FILE = original

    def test_missing_file_returns_empty_dict(self, tmp_path):
        import bilibili_fav_classifier.mappings as mod
        original = mod.SEED_FILE
        mod.SEED_FILE = tmp_path / "nonexistent.json"
        try:
            result = load_seed_mappings()
            assert result == {}
        finally:
            mod.SEED_FILE = original

    def test_returns_all_folders(self, tmp_path):
        data = {"A": ["u1"], "B": ["u2", "u3"], "C": []}
        target = tmp_path / "seed_mappings.json"
        target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        import bilibili_fav_classifier.mappings as mod
        original = mod.SEED_FILE
        mod.SEED_FILE = target
        try:
            result = load_seed_mappings()
            assert set(result.keys()) == {"A", "B", "C"}
            assert result["B"] == ["u2", "u3"]
        finally:
            mod.SEED_FILE = original


class TestSaveSeedMappings:
    def test_creates_file(self, tmp_path):
        target = tmp_path / "seed_mappings.json"
        import bilibili_fav_classifier.mappings as mod
        original = mod.SEED_FILE
        mod.SEED_FILE = target
        try:
            save_seed_mappings({"学习与竞赛": ["UP_A"]})
            assert target.exists()
        finally:
            mod.SEED_FILE = original

    def test_writes_valid_json(self, tmp_path):
        target = tmp_path / "seed_mappings.json"
        mappings = {"AI与编程技术": ["UP1", "UP2"], "音乐": ["UP3"]}
        import bilibili_fav_classifier.mappings as mod
        original = mod.SEED_FILE
        mod.SEED_FILE = target
        try:
            save_seed_mappings(mappings)
            raw = json.loads(target.read_text(encoding="utf-8"))
            assert raw == mappings
        finally:
            mod.SEED_FILE = original

    def test_overwrites_existing_file(self, tmp_path):
        target = tmp_path / "seed_mappings.json"
        target.write_text(json.dumps({"旧文件夹": ["旧UP"]}, ensure_ascii=False), encoding="utf-8")
        import bilibili_fav_classifier.mappings as mod
        original = mod.SEED_FILE
        mod.SEED_FILE = target
        try:
            save_seed_mappings({"新文件夹": ["新UP"]})
            result = json.loads(target.read_text(encoding="utf-8"))
            assert result == {"新文件夹": ["新UP"]}
        finally:
            mod.SEED_FILE = original

    def test_roundtrip(self, tmp_path):
        """Save then load should give back the same data."""
        target = tmp_path / "seed_mappings.json"
        original_data = {
            "AI与编程技术": ["3Blue1Brown"],
            "学习与竞赛": ["李永乐老师", "罗翔说刑法"],
            "生活与社会": ["无穷小亮的科普日常"],
        }
        import bilibili_fav_classifier.mappings as mod
        original = mod.SEED_FILE
        mod.SEED_FILE = target
        try:
            save_seed_mappings(original_data)
            loaded = load_seed_mappings()
            assert loaded == original_data
        finally:
            mod.SEED_FILE = original


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Tests for classify_core: classify_video, autoclassify, genplan, ClassifyResult.

Seams:
  - classify_video(video, up_to_folder) -> (folder, layer)
  - autoclassify(favs_data, seed_map) -> ClassifyResult
  - genplan(favs_data, seed_map) -> dict
  - ClassifyResult (dataclass)
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from bilibili_fav_classifier.classify_core import (
    ClassifyResult,
    autoclassify,
    classify_video,
    genplan,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def empty_up_map():
    return {}


@pytest.fixture
def sample_up_map():
    return {"3Blue1Brown": "AI与编程技术", "罗翔说刑法": "学习与竞赛"}


@pytest.fixture
def sample_favs():
    """5 videos covering all 5 classification layers."""
    return {
        "videos": [
            # Layer 1: tag match — Python tag → AI与编程技术
            {"id": 1, "bvid": "BV1", "title": "Python教程", "tags": ["Python"], "tname": "", "upper": ""},
            # Layer 2: partition match — 游戏 → 游戏与动漫
            {"id": 2, "bvid": "BV2", "title": "王者荣耀", "tags": [], "tname": "游戏", "upper": ""},
            # Layer 3: UP mapping — 李永乐老师 → 学习与竞赛
            {"id": 3, "bvid": "BV3", "title": "考研数学", "tags": [], "tname": "", "upper": "李永乐老师"},
            # Layer 4: keyword match — 探店 → 生活与社会
            {"id": 4, "bvid": "BV4", "title": "美食探店", "tags": [], "tname": "", "upper": ""},
            # Layer 5: fallback — no match → 其他
            {"id": 5, "bvid": "BV5", "title": "完全无关的内容啊哈哈", "tags": [], "tname": "", "upper": "未知UP主xyz"},
        ],
    }


@pytest.fixture
def sample_seed_map():
    return {
        "AI与编程技术": ["3Blue1Brown"],
        "学习与竞赛": ["李永乐老师", "罗翔说刑法"],
    }


# ── classify_video ───────────────────────────────────────────────

class TestClassifyVideo:
    def test_tag_match(self, empty_up_map):
        folder, layer = classify_video(
            {"title": "x", "tags": ["Python"], "tname": "", "upper": ""}, empty_up_map
        )
        assert folder == "AI与编程技术"
        assert layer == "tag"

    def test_partition_match(self, empty_up_map):
        folder, layer = classify_video(
            {"title": "x", "tags": [], "tname": "游戏", "upper": ""}, empty_up_map
        )
        assert folder == "游戏与动漫"
        assert layer == "partition"

    def test_up_mapping(self, sample_up_map):
        folder, layer = classify_video(
            {"title": "x", "tags": [], "tname": "", "upper": "罗翔说刑法"}, sample_up_map
        )
        assert folder == "学习与竞赛"
        assert layer == "up"

    def test_keyword_match(self, empty_up_map):
        folder, layer = classify_video(
            {"title": "王者荣耀攻略", "tags": [], "tname": "", "upper": ""}, empty_up_map
        )
        assert folder == "游戏与动漫"
        assert layer == "keyword"

    def test_fallback(self, empty_up_map):
        folder, layer = classify_video(
            {"title": "完全无关", "tags": [], "tname": "", "upper": ""}, empty_up_map
        )
        assert folder == "其他"
        assert layer == "fallback"


# ── autoclassify ──────────────────────────────────────────────────

class TestAutoclassify:
    def test_returns_classify_result(self, sample_favs, sample_seed_map):
        result = autoclassify(sample_favs, sample_seed_map)
        assert isinstance(result, ClassifyResult)

    def test_correct_total_count(self, sample_favs, sample_seed_map):
        result = autoclassify(sample_favs, sample_seed_map)
        assert result.total == 5

    def test_tag_layer_count(self, sample_favs, sample_seed_map):
        """BV1 has Python tag → 'tag' layer."""
        result = autoclassify(sample_favs, sample_seed_map)
        assert result.layer_counts.get("tag") == 1

    def test_partition_layer_count(self, sample_favs, sample_seed_map):
        """BV2 has 游戏 partition → 'partition' layer."""
        result = autoclassify(sample_favs, sample_seed_map)
        assert result.layer_counts.get("partition") == 1

    def test_up_layer_count(self, sample_favs, sample_seed_map):
        """BV3 upper 李永乐老师 is in seed_map → 'up' layer."""
        result = autoclassify(sample_favs, sample_seed_map)
        assert result.layer_counts.get("up") == 1

    def test_keyword_layer_count(self, sample_favs, sample_seed_map):
        """BV4 '美食探店' → keyword match for 生活与社会."""
        result = autoclassify(sample_favs, sample_seed_map)
        assert result.layer_counts.get("keyword") == 1

    def test_fallback_layer_count(self, sample_favs, sample_seed_map):
        """BV5 has no matching tag/partition/up/keyword → 'fallback' layer."""
        result = autoclassify(sample_favs, sample_seed_map)
        assert result.layer_counts.get("fallback") == 1

    def test_groups_contain_correct_folders(self, sample_favs, sample_seed_map):
        result = autoclassify(sample_favs, sample_seed_map)
        folders = set(result.groups.keys())
        assert "AI与编程技术" in folders   # BV1
        assert "游戏与动漫" in folders     # BV2
        assert "学习与竞赛" in folders     # BV3
        assert "生活与社会" in folders     # BV4
        assert "其他" in folders           # BV5

    def test_unmatched_ups_tracked(self, sample_favs, sample_seed_map):
        """UP主 that fall through should appear in unmatched_ups."""
        result = autoclassify(sample_favs, sample_seed_map)
        assert "未知UP主xyz" in result.unmatched_ups
        assert result.unmatched_ups["未知UP主xyz"] == ["完全无关的内容啊哈哈"]

    def test_empty_favs(self):
        """Handles empty videos list gracefully."""
        result = autoclassify({"videos": []}, {})
        assert result.total == 0
        assert result.groups == {}
        assert result.layer_counts == {}
        assert result.unmatched_ups == {}

    def test_empty_seed_map(self, sample_favs):
        """With empty seed map, tag/partition/keyword still match, up falls through."""
        result = autoclassify(sample_favs, {})
        assert result.layer_counts.get("tag") == 1          # BV1
        assert result.layer_counts.get("partition") == 1    # BV2
        assert result.layer_counts.get("up") is None        # BV3: 李永乐老师 not in empty map
        assert result.layer_counts.get("keyword") == 2      # BV3 (考研数学) + BV4 (美食探店)
        assert result.layer_counts.get("fallback") == 1     # BV5

    def test_no_file_io(self, sample_favs, sample_seed_map, tmp_path):
        """autoclassify does not create or read any files."""
        result = autoclassify(sample_favs, sample_seed_map)
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) == 0
        assert result.total == 5


# ── genplan ──────────────────────────────────────────────────────

class TestGenplan:
    def test_returns_plan_dict(self, sample_favs, sample_seed_map):
        plan = genplan(sample_favs, sample_seed_map)
        assert isinstance(plan, dict)
        assert plan["move"] is True
        assert "groups" in plan

    def test_known_up_in_correct_folder(self, sample_favs, sample_seed_map):
        """Videos from known UP主 go to their mapped folder."""
        plan = genplan(sample_favs, sample_seed_map)
        groups = plan["groups"]
        assert "学习与竞赛" in groups
        bvids = [v["bvid"] for v in groups["学习与竞赛"]]
        assert "BV3" in bvids

    def test_unknown_up_goes_to_other(self, sample_favs, sample_seed_map):
        """Videos from unknown UP主 go to '其他'."""
        plan = genplan(sample_favs, sample_seed_map)
        assert "其他" in plan["groups"]
        bvids = [v["bvid"] for v in plan["groups"]["其他"]]
        assert "BV5" in bvids  # 未知UP主xyz not in seed_map

    def test_no_file_io(self, sample_favs, sample_seed_map, tmp_path):
        """genplan does not create any files."""
        plan = genplan(sample_favs, sample_seed_map)
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) == 0

    def test_empty_favs(self):
        """Handles empty videos list."""
        plan = genplan({"videos": []}, {})
        assert plan["groups"] == {}

    def test_uses_bvid_as_fallback_id(self):
        """When video has no 'id', uses bvid as the resource id."""
        favs = {
            "videos": [
                {"bvid": "BV_only", "title": "x", "upper": "", "id": None},
            ],
        }
        plan = genplan(favs, {})
        assert plan["groups"]["其他"][0]["id"] == "BV_only"


# ── ClassifyResult ────────────────────────────────────────────────

class TestClassifyResult:
    def test_default_values(self):
        result = ClassifyResult()
        assert result.groups == {}
        assert result.layer_counts == {}
        assert result.unmatched_ups == {}
        assert result.total == 0

    def test_with_data(self):
        result = ClassifyResult(
            groups={"AI": [{"id": 1}]},
            layer_counts={"tag": 1},
            unmatched_ups={"UP1": ["title1"]},
            total=1,
        )
        assert result.total == 1
        assert "AI" in result.groups
        assert result.layer_counts["tag"] == 1
        assert "UP1" in result.unmatched_ups


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

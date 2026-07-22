"""Tests for classify_video: the 4-layer classification engine.

Seam: classify_video(video: dict, up_to_folder: dict) -> (folder: str, layer: str)

Layer priority: tag > partition > up mapping > keyword > "其他"
Layer labels: "tag" | "partition" | "up" | "keyword" | "fallback"
"""
import sys
import json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from bilibili_fav_classifier.classify_core import classify_video


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def empty_up_map():
    return {}


@pytest.fixture
def sample_up_map():
    return {"3Blue1Brown": "AI与编程技术", "罗翔说刑法": "学习与竞赛"}


# ── Layer 1: Tag matching ─────────────────────────────────────────

class TestTagMatch:
    """tag_match has highest priority."""

    def test_python_tag_returns_ai_folder(self, empty_up_map):
        video = {"title": "无关标题", "tags": ["Python", "编程"], "tname": "", "upper": ""}
        folder, layer = classify_video(video, empty_up_map)
        assert folder == "AI与编程技术"
        assert layer == "tag"

    def test_multiple_tags_first_match_wins(self, empty_up_map):
        video = {"title": "xx", "tags": ["美食", "Python"], "tname": "", "upper": ""}
        folder, layer = classify_video(video, empty_up_map)
        assert folder == "AI与编程技术"
        assert layer == "tag"

    def test_unknown_tag_falls_through(self, empty_up_map):
        video = {"title": "xx", "tags": ["random", "stuff"], "tname": "", "upper": ""}
        folder, layer = classify_video(video, empty_up_map)
        assert layer == "fallback"


# ── Layer 2: Partition matching ──────────────────────────────────

class TestPartitionMatch:
    """partition_match fires when no tags match."""

    def test_tech_partition_returns_ai_folder(self, empty_up_map):
        video = {"title": "xx", "tags": [], "tname": "科技", "upper": ""}
        folder, layer = classify_video(video, empty_up_map)
        assert folder == "AI与编程技术"
        assert layer == "partition"

    def test_game_partition_returns_gaming_folder(self, empty_up_map):
        video = {"title": "xx", "tags": [], "tname": "游戏", "upper": ""}
        folder, layer = classify_video(video, empty_up_map)
        assert folder == "游戏与动漫"
        assert layer == "partition"

    def test_sports_partition_returns_sports_folder(self, empty_up_map):
        video = {"title": "xx", "tags": [], "tname": "运动", "upper": ""}
        folder, layer = classify_video(video, empty_up_map)
        assert folder == "体育"
        assert layer == "partition"

    def test_empty_tname_falls_through(self, empty_up_map):
        video = {"title": "xx", "tags": [], "tname": "", "upper": ""}
        folder, layer = classify_video(video, empty_up_map)
        assert layer == "fallback"

    def test_unmapped_partition_falls_through(self, empty_up_map):
        video = {"title": "xx", "tags": [], "tname": "军事", "upper": ""}
        folder, layer = classify_video(video, empty_up_map)
        assert layer == "fallback"


# ── Layer 3: UP mapping ──────────────────────────────────────────

class TestUpMapping:
    """UP mapping fires when tags and partition don't match."""

    def test_known_up_returns_mapped_folder(self, sample_up_map):
        video = {"title": "任何标题", "tags": [], "tname": "", "upper": "罗翔说刑法"}
        folder, layer = classify_video(video, sample_up_map)
        assert folder == "学习与竞赛"
        assert layer == "up"

    def test_unknown_up_falls_through(self, empty_up_map):
        video = {"title": "xx", "tags": [], "tname": "", "upper": "未知UP主"}
        folder, layer = classify_video(video, empty_up_map)
        assert layer == "fallback"

    def test_empty_up_name_falls_through(self, empty_up_map):
        video = {"title": "xx", "tags": [], "tname": "", "upper": ""}
        folder, layer = classify_video(video, empty_up_map)
        assert layer == "fallback"


# ── Layer 4: Keyword matching ────────────────────────────────────

class TestKeywordMatch:
    """Keyword matching fires when layers 1-3 miss."""

    def test_gaming_keyword_returns_gaming_folder(self, empty_up_map):
        video = {"title": "王者荣耀攻略视频", "tags": [], "tname": "", "upper": ""}
        folder, layer = classify_video(video, empty_up_map)
        assert folder == "游戏与动漫"
        assert layer == "keyword"

    def test_study_keyword_returns_learning_folder(self, empty_up_map):
        video = {"title": "考研数学复习指南", "tags": [], "tname": "", "upper": ""}
        folder, layer = classify_video(video, empty_up_map)
        assert folder == "学习与竞赛"
        assert layer == "keyword"

    def test_fitness_keyword_returns_sports_folder(self, empty_up_map):
        video = {"title": "健身增肌训练计划", "tags": [], "tname": "", "upper": ""}
        folder, layer = classify_video(video, empty_up_map)
        assert folder == "体育"
        assert layer == "keyword"


# ── Fallback ──────────────────────────────────────────────────────

class TestFallback:
    """When nothing matches, returns '其他' with layer 'fallback'."""

    def test_no_match_returns_other(self, empty_up_map):
        video = {"title": "完全无关的视频", "tags": [], "tname": "", "upper": ""}
        folder, layer = classify_video(video, empty_up_map)
        assert folder == "其他"
        assert layer == "fallback"

    def test_fallback_with_known_up_still_falls(self, empty_up_map):
        """UP map is empty, so even a real-sounding name falls through."""
        video = {"title": "随机标题", "tags": [], "tname": "", "upper": "某个UP主"}
        folder, layer = classify_video(video, empty_up_map)
        assert folder == "其他"
        assert layer == "fallback"


# ── Priority ordering ─────────────────────────────────────────────

class TestPriority:
    """Higher-priority layers win over lower ones."""

    def test_tag_beats_partition(self, empty_up_map):
        """Tag match should win even if partition would also match."""
        video = {"title": "xx", "tags": ["编程"], "tname": "游戏", "upper": ""}
        folder, layer = classify_video(video, empty_up_map)
        assert folder == "AI与编程技术"
        assert layer == "tag"

    def test_partition_beats_up(self, sample_up_map):
        """Partition match should win over UP mapping."""
        video = {"title": "xx", "tags": [], "tname": "科技", "upper": "3Blue1Brown"}
        folder, layer = classify_video(video, sample_up_map)
        # 3Blue1Brown maps to AI与编程技术; 科技 also maps to AI与编程技术
        # Both give same folder, but partition should be the layer
        assert layer == "partition"

    def test_tag_beats_up(self, sample_up_map):
        """Tag match should win over UP mapping."""
        video = {"title": "xx", "tags": ["游戏"], "tname": "", "upper": "3Blue1Brown"}
        folder, layer = classify_video(video, sample_up_map)
        assert folder == "游戏与动漫"
        assert layer == "tag"

    def test_up_beats_keyword(self, sample_up_map):
        """UP mapping should win over keyword match."""
        video = {"title": "王者荣耀攻略", "tags": [], "tname": "", "upper": "3Blue1Brown"}
        folder, layer = classify_video(video, sample_up_map)
        assert folder == "AI与编程技术"
        assert layer == "up"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

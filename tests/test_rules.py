"""Tests for classification rules: tag_match, partition_match, keyword_classify.

Seams:
  - tag_match(tags: list[str] | None) -> str | None
  - partition_match(tname: str | None) -> str | None
  - keyword_classify(title: str) -> str | None
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from bilibili_fav_classifier.rules import keyword_classify, partition_match, tag_match


# ── tag_match ─────────────────────────────────────────────────────

class TestTagMatchRules:
    def test_single_ai_tag(self):
        assert tag_match(["Python"]) == "AI与编程技术"

    def test_single_study_tag(self):
        assert tag_match(["考研"]) == "学习与竞赛"

    def test_single_game_tag(self):
        assert tag_match(["原神"]) == "游戏与动漫"

    def test_single_sports_tag(self):
        assert tag_match(["健身"]) == "体育"

    def test_single_music_tag(self):
        assert tag_match(["钢琴"]) == "音乐"

    def test_single_emotion_tag(self):
        assert tag_match(["治愈"]) == "情感与文案"

    def test_single_history_tag(self):
        assert tag_match(["二战"]) == "历史与时政"

    def test_single_life_tag(self):
        assert tag_match(["美食"]) == "生活与社会"

    def test_case_insensitive(self):
        assert tag_match(["PYTHON"]) == "AI与编程技术"

    def test_mixed_tags_rule_order_determines_winner(self):
        """tag_match joins all tags then checks rules in TAG_RULES order."""
        video = {"title": "xx", "tags": ["美食", "Python"], "tname": "", "upper": ""}
        # "Python" is in the first TAG_RULE (AI), so AI wins over 美食 (生活与社会)
        assert tag_match(["美食", "Python"]) == "AI与编程技术"

    def test_none_tags_returns_none(self):
        assert tag_match(None) is None

    def test_empty_list_returns_none(self):
        assert tag_match([]) is None

    def test_no_matching_tag_returns_none(self):
        assert tag_match(["random", "xyz"]) is None


# ── partition_match ──────────────────────────────────────────────

class TestPartitionMatchRules:
    def test_tech_partition(self):
        assert partition_match("科技") == "AI与编程技术"

    def test_digital_partition(self):
        assert partition_match("数码") == "AI与编程技术"

    def test_knowledge_partition(self):
        assert partition_match("知识") == "学习与竞赛"

    def test_game_partition(self):
        assert partition_match("游戏") == "游戏与动漫"

    def test_sports_partition(self):
        assert partition_match("运动") == "体育"

    def test_music_partition(self):
        assert partition_match("音乐") == "音乐"

    def test_life_partition(self):
        assert partition_match("生活") == "生活与社会"

    def test_docu_partition(self):
        assert partition_match("纪录片") == "生活与社会"

    def test_none_tname_returns_none(self):
        assert partition_match(None) is None

    def test_empty_string_returns_none(self):
        assert partition_match("") is None

    def test_unmapped_partition_returns_none(self):
        assert partition_match("军事") is None


# ── keyword_classify ─────────────────────────────────────────────

class TestKeywordClassifyRules:
    def test_ai_keyword(self):
        assert keyword_classify("Python教程") == "AI与编程技术"

    def test_study_keyword(self):
        assert keyword_classify("考研数学") == "学习与竞赛"

    def test_game_keyword(self):
        assert keyword_classify("王者荣耀攻略") == "游戏与动漫"

    def test_sports_keyword(self):
        assert keyword_classify("健身增肌") == "体育"

    def test_music_keyword(self):
        assert keyword_classify("钢琴演奏") == "音乐"

    def test_emotion_keyword(self):
        assert keyword_classify("情感治愈文案") == "情感与文案"

    def test_history_keyword(self):
        assert keyword_classify("二战历史") == "历史与时政"

    def test_life_keyword(self):
        assert keyword_classify("美食探店") == "生活与社会"

    def test_case_insensitive(self):
        assert keyword_classify("PYTHON") == "AI与编程技术"

    def test_empty_title_returns_none(self):
        assert keyword_classify("") is None

    def test_no_keyword_returns_none(self):
        assert keyword_classify("完全无关的内容啊哈哈哈") is None

    def test_partial_match(self):
        """Keyword can appear anywhere in the title."""
        assert keyword_classify("我的Python学习笔记") == "AI与编程技术"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

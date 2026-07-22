"""B站收藏夹智能分类工具.

Pipeline: collect → enrich_meta → autoclassify → apply
"""
from bilibili_fav_classifier.apply import apply
from bilibili_fav_classifier.classify_core import autoclassify, classify_video, genplan
from bilibili_fav_classifier.collect import collect
from bilibili_fav_classifier.config import (
    API_BASE,
    APPLY_LOG_JSON,
    BATCH_SIZE,
    COOKIES_PATH,
    DEFAULT_FAV_ID,
    ENRICH_CACHE_JSON,
    FAVS_JSON,
    PLAN_JSON,
    USER_MID,
)
from bilibili_fav_classifier.enrich import enrich_meta
from bilibili_fav_classifier.rules import (
    KEYWORD_RULES,
    PARTITION_RULES,
    TAG_RULES,
    keyword_classify,
    partition_match,
    tag_match,
)
from bilibili_fav_classifier.session import HttpClient, Session, save_cookies

__all__ = [
    # Pipeline
    "autoclassify",
    "classify_video",
    "collect",
    "enrich_meta",
    "genplan",
    "apply",
    # Config
    "API_BASE",
    "APPLY_LOG_JSON",
    "BATCH_SIZE",
    "COOKIES_PATH",
    "DEFAULT_FAV_ID",
    "ENRICH_CACHE_JSON",
    "FAVS_JSON",
    "PLAN_JSON",
    "USER_MID",
    # Rules
    "KEYWORD_RULES",
    "PARTITION_RULES",
    "TAG_RULES",
    "keyword_classify",
    "partition_match",
    "tag_match",
    # Session
    "HttpClient",
    "Session",
    "save_cookies",
    # Config helpers
    "USER_MID",
]

"""B站收藏夹智能分类工具.

Three-step workflow:
  1. collect    — scrape your default favorite folder
  2. enrich_meta — supplement video tags/partition via video detail API
  3. autoclassify — auto-classify via tags → partition → UP mapping → keywords
  4. apply      — create folders and move videos
"""
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
    get_cookies,
    get_csrf,
)
from bilibili_fav_classifier.rules import (
    KEYWORD_RULES,
    PARTITION_RULES,
    TAG_RULES,
    keyword_classify,
    load_seed_mappings,
    partition_match,
    tag_match,
)
from bilibili_fav_classifier.mappings import save_seed_mappings
from bilibili_fav_classifier.classify import classify_video

__all__ = [
    "classify",
    "config",
    "rules",
    "API_BASE",
    "APPLY_LOG_JSON",
    "BATCH_SIZE",
    "COOKIES_PATH",
    "DEFAULT_FAV_ID",
    "ENRICH_CACHE_JSON",
    "FAVS_JSON",
    "PLAN_JSON",
    "USER_MID",
    "KEYWORD_RULES",
    "PARTITION_RULES",
    "TAG_RULES",
    "classify_video",
    "get_cookies",
    "get_csrf",
    "keyword_classify",
    "load_seed_mappings",
    "partition_match",
    "save_seed_mappings",
    "tag_match",
]

"""B站收藏夹智能分类工具.

Three-step workflow:
  1. collect    — scrape your default favorite folder
  2. autoclassify — auto-classify via manual mappings + keyword matching
  3. apply      — create folders and move videos
"""
from bilibili_fav_classifier.config import (
    API_BASE,
    APPLY_LOG_JSON,
    BATCH_SIZE,
    COOKIES_PATH,
    DEFAULT_FAV_ID,
    FAVS_JSON,
    MANUAL_MAP_JSON,
    PLAN_JSON,
    USER_MID,
    get_cookies,
    get_csrf,
)
from bilibili_fav_classifier.mappings import DEFAULT_MAPPINGS, load_mappings, save_mappings

__all__ = [
    "classify",
    "config",
    "mappings",
    "API_BASE",
    "APPLY_LOG_JSON",
    "BATCH_SIZE",
    "COOKIES_PATH",
    "DEFAULT_FAV_ID",
    "FAVS_JSON",
    "MANUAL_MAP_JSON",
    "PLAN_JSON",
    "USER_MID",
    "DEFAULT_MAPPINGS",
    "get_cookies",
    "get_csrf",
    "load_mappings",
    "save_mappings",
]

"""User-specific configuration for bilibili-fav-classifier."""
from pathlib import Path

ROOT = Path(__file__).parent

USER_MID = ""                    # 改成你的 B站用户 ID（纯数字字符串）
DEFAULT_FAV_ID = 0               # 改成你的「默认收藏夹」ID

COOKIES_PATH = ROOT / "cookies.json"
FAVS_JSON = ROOT / "favs.json"
PLAN_JSON = ROOT / "plan.json"
APPLY_LOG_JSON = ROOT / "apply_log.json"
ENRICH_CACHE_JSON = ROOT / "enrich_cache.json"   # 标签/分区缓存
AUTO_CLASSIFY_JSON = ROOT / "auto_classified.json"

BATCH_SIZE = 50
API_BASE = "https://api.bilibili.com"

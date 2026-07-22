"""User-specific configuration for bilibili-fav-classifier."""
import json
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

# Shared HTTP headers for all Bilibili API calls
DEFAULT_HEADERS = {
    "Referer": "https://www.bilibili.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        " AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/120.0.0.0 Safari/537.36"
    ),
}


def get_cookies() -> dict:
    if not COOKIES_PATH.exists():
        raise FileNotFoundError(
            f"cookies.json not found at {COOKIES_PATH}. "
            "Run 'python -m bilibili_fav_classifier collect' first."
        )
    raw = json.loads(COOKIES_PATH.read_text(encoding="utf-8"))
    return {c["name"]: c["value"] for c in raw}


def get_csrf(cookies: dict) -> str:
    csrf = cookies.get("bili_jct", "")
    if not csrf:
        raise ValueError("No bili_jct in cookies. Re-run collect to login.")
    return csrf

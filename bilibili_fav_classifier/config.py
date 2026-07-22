"""User-specific configuration for bilibili-fav-classifier."""
import json
from pathlib import Path

ROOT = Path(__file__).parent

USER_MID = "350016742"

DEFAULT_FAV_ID = 197359242

COOKIES_PATH = ROOT / "cookies.json"
FAVS_JSON = ROOT / "favs.json"
PLAN_JSON = ROOT / "plan.json"
APPLY_LOG_JSON = ROOT / "apply_log.json"
MANUAL_MAP_JSON = ROOT / "up_mappings.json"
AUTO_CLASSIFY_JSON = ROOT / "auto_classified.json"

BATCH_SIZE = 50
API_BASE = "https://api.bilibili.com"


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

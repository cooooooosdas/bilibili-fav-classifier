"""User-specific configuration for bilibili-fav-classifier."""
from __future__ import annotations

import json
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).parent
else:
    ROOT = Path(__file__).parent

COOKIES_PATH = ROOT / "cookies.json"
FAVS_JSON = ROOT / "favs.json"
PLAN_JSON = ROOT / "plan.json"
APPLY_LOG_JSON = ROOT / "apply_log.json"
ENRICH_CACHE_JSON = ROOT / "enrich_cache.json"
AUTO_CLASSIFY_JSON = ROOT / "auto_classified.json"

BATCH_SIZE = 50
API_BASE = "https://api.bilibili.com"


def load_user_config() -> dict:
    """Load user config from config.json (created on first run)."""
    config_file = ROOT / "config.json"
    if config_file.exists():
        try:
            return json.loads(config_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"警告: {config_file} 格式错误，使用默认配置")
            return {}
    return {}


def save_user_config(user_mid: str, default_fav_id: int):
    """Persist user config to config.json for future runs."""
    config_file = ROOT / "config.json"
    config_file.write_text(
        json.dumps({"USER_MID": user_mid, "DEFAULT_FAV_ID": default_fav_id}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Loaded from config.json at import time — no hardcoded personal data
_user_cfg = load_user_config()
USER_MID: str = _user_cfg.get("USER_MID", "")
DEFAULT_FAV_ID: int = _user_cfg.get("DEFAULT_FAV_ID", 0)

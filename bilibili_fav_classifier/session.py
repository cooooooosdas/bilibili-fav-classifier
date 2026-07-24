"""Session management: cookie loading, CSRF extraction, HTTP client.

Single source of truth for all cookie/CSRF/HTTP operations.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import requests

from bilibili_fav_classifier.config import COOKIES_PATH

DEFAULT_HEADERS = {
    "Referer": "https://www.bilibili.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        " AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/120.0.0.0 Safari/537.36"
    ),
}


@dataclass
class Session:
    """Authenticated Bilibili session."""
    cookies: dict[str, str]
    csrf: str
    headers: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_HEADERS))
    mid: str = ""

    @classmethod
    def load(cls) -> Session:
        """Load cookies from disk and extract CSRF token + mid."""
        try:
            raw = json.loads(COOKIES_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ValueError("cookies.json 不存在，请先运行 collect 登录") from None
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"cookies.json 格式错误: {exc}") from None
        cookies = {c["name"]: c["value"] for c in raw}
        csrf = cookies.get("bili_jct", "")
        if not csrf:
            raise ValueError("No bili_jct in cookies. Re-run collect to login.")
        from bilibili_fav_classifier.config import load_user_config
        mid = load_user_config().get("USER_MID", "")
        return cls(cookies=cookies, csrf=csrf, mid=mid)

    def http(self) -> HttpClient:
        """Create an HTTP client bound to this session."""
        return HttpClient(cookies=self.cookies, headers=self.headers)


class HttpClient:
    """HTTP client bound to a session. Injectable for testing."""

    def __init__(self, cookies: dict, headers: dict | None = None):
        self.cookies = cookies
        self.headers = headers or dict(DEFAULT_HEADERS)

    def get(self, url: str) -> dict:
        r = requests.get(url, cookies=self.cookies, headers=self.headers, timeout=15)
        return r.json()

    def post(self, url: str, data: dict) -> dict:
        try:
            r = requests.post(url, data=data, cookies=self.cookies, headers=self.headers, timeout=15)
            ct = r.headers.get("content-type", "")
            if "json" not in ct.lower():
                return {"_waf_html": True, "_status": r.status_code, "_ctype": ct}
            return r.json()
        except requests.exceptions.JSONDecodeError:
            return {"_waf_html": True, "_error": "json_decode"}
        except Exception as e:
            return {"_error": True, "_msg": str(e)}


async def save_cookies(context) -> None:
    """Save Playwright browser cookies to disk."""
    cookies = await context.cookies()
    COOKIES_PATH.write_text(
        json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"==> 已保存 {len(cookies)} 个 cookies 到 {COOKIES_PATH}")

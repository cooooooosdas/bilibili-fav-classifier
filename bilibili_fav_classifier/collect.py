"""Async browser automation: collect all videos from the default favorite folder.

Entry point: collect() — launches Playwright, logs in via QR, scrapes favorites.
"""
from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from bilibili_fav_classifier.config import (
    API_BASE,
    COOKIES_PATH,
    DEFAULT_FAV_ID,
    FAVS_JSON,
    USER_MID,
)
from bilibili_fav_classifier.session import save_cookies

_CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
CHROME_PATH = next((p for p in _CHROME_CANDIDATES if Path(p).exists()), None)
BROWSER_ARGS = [
    "--disable-web-security",
    "--disable-features=IsolateOrigins,site-per-process",
    "--no-sandbox",
    "--disable-gpu",
]


async def wait_for_login(page, timeout: int = 180):
    """Poll until the user is logged in, return their mid."""
    print("==> 请在浏览器中扫码登录 B站 (若已登录会自动跳过)...")
    for _ in range(timeout // 2):
        mid = await page.evaluate('''async () => {
            try {
                const r = await fetch("https://api.bilibili.com/x/web-interface/nav");
                const j = await r.json();
                return j.data?.isLogin ? j.data.mid : null;
            } catch (e) { return null; }
        }''')
        if mid:
            return mid
        await asyncio.sleep(2)
    return None


async def collect():
    """Launch browser, log in, scrape all videos from default favorite folder."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, executable_path=CHROME_PATH, args=BROWSER_ARGS,
        )
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(
            f"https://space.bilibili.com/{USER_MID}/favlist?fid={DEFAULT_FAV_ID}",
            wait_until="domcontentloaded",
        )
        await asyncio.sleep(3)

        mid = await wait_for_login(page)
        if not mid:
            print("==> 登录超时, 请重新运行 collect")
            await context.close()
            return
        print(f"==> 登录用户 mid={mid}")
        await save_cookies(context)

        folders = await page.evaluate(f'''async () => {{
            const r = await fetch(
                "{API_BASE}/x/v3/fav/folder/created/list-all"
                + "?up_mid={USER_MID}&platform=web"
            );
            const j = await r.json();
            return j.data?.list || [];
        }}''')
        print(f"==> 你的收藏夹 ({len(folders)} 个):")
        for f in folders:
            print(
                f"    - {f.get('title')}"
                f"  (id={f.get('id')}, 数量={f.get('media_count')})"
            )

        default = next(
            (f for f in folders if "默认" in (f.get("title") or "")), None
        )
        default_id = default.get("id") if default else DEFAULT_FAV_ID
        print(f"==> 默认收藏夹: {default.get('title') if default else '默认'}"
              f" (id={default_id})")
        print("==> 正在拉取默认收藏夹的全部视频...")

        all_items = await page.evaluate(f'''async () => {{
            const all = [];
            for (let pn = 1; pn <= 200; pn++) {{
                const r = await fetch(
                    "{API_BASE}/x/v3/fav/resource/list"
                    + "?media_id={DEFAULT_FAV_ID}&pn=" + pn
                    + "&ps=20&platform=web&order=mtime"
                );
                const j = await r.json();
                if (j.code !== 0) {{ all.push({{error:true,code:j.code,page:pn}}); break; }}
                const medias = j.data?.medias || [];
                all.push(...medias);
                if (!j.data?.has_more || medias.length === 0) break;
                await new Promise(res => setTimeout(res, 800));
            }}
            return all;
        }}''')

        items = [it for it in all_items if not it.get("error")]
        errors = [it for it in all_items if it.get("error")]
        if errors:
            for e in errors:
                print(f"    [warn] 第{e.get('page')}页 code={e.get('code')}")
        print(f"==> 共拉取 {len(items)} 条视频")

        videos = []
        for it in items:
            upper = it.get("upper") or {}
            videos.append({
                "id": it.get("id"),
                "bvid": it.get("bvid"),
                "title": (
                    (it.get("title") or "")
                    .replace('<em class="keyword">', "")
                    .replace("</em>", "")
                ),
                "upper": upper.get("name", ""),
                "upper_mid": upper.get("mid"),
                "tname": it.get("tname", ""),
                "tags": it.get("tag", []),
            })

        FAVS_JSON.write_text(
            json.dumps(
                {
                    "mid": mid,
                    "default_media_id": default_id,
                    "count": len(videos),
                    "videos": videos,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"==> 已保存到 {FAVS_JSON}")

        up_map: dict[str, list[str]] = defaultdict(list)
        for v in videos:
            up = v.get("upper") or "未知UP"
            up_map[up].append(v.get("title", ""))
        uppers = [
            {"upper": up, "count": len(ts), "samples": ts[:5]}
            for up, ts in up_map.items()
        ]
        uppers.sort(key=lambda x: x["count"], reverse=True)
        summary_path = Path(__file__).parent / "up_summary.json"
        summary_path.write_text(
            json.dumps({"total": len(videos), "uppers": uppers}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"==> 已生成 {summary_path} ({len(uppers)} 个UP主)")
        print("==> 下一步: 运行 enrich_meta 补充标签/分区, 再 autoclassify")
        await context.close()
        await browser.close()

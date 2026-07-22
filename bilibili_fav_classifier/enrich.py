"""Enrich video metadata: fetch tags and partition (tname) via video detail API.

Uses file-based cache (enrich_cache.json) to avoid re-fetching.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from bilibili_fav_classifier.config import (
    API_BASE,
    ENRICH_CACHE_JSON,
    FAVS_JSON,
)
from bilibili_fav_classifier.session import Session


def _fetch_video_meta(bvid: str, session: Session) -> dict:
    """Fetch video detail to get tname (partition) and tags."""
    try:
        r = requests.get(
            f"{API_BASE}/x/web-interface/view?bvid={bvid}",
            cookies=session.cookies, headers=session.headers, timeout=15,
        )
        j = r.json()
        if j.get("code") != 0:
            return {}
        data = j.get("data", {})
        tags = [t.get("tag_name", "") for t in data.get("tags", [])]
        return {"tname": data.get("tname", ""), "tags": tags}
    except Exception:
        return {}


def enrich_meta(session: Session | None = None) -> None:
    """Supplement tname and tags for each video by calling the video detail API.

    Args:
        session: Authenticated session. If None, loads from disk.
    """
    if not FAVS_JSON.exists():
        print("==> 请先运行 collect")
        return

    if session is None:
        session = Session.load()

    cache_path = ENRICH_CACHE_JSON
    cache: dict[str, dict] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    favs = json.loads(FAVS_JSON.read_text(encoding="utf-8"))
    videos = favs.get("videos", [])

    need_fetch = []
    for v in videos:
        bvid = v.get("bvid", "")
        if not bvid:
            continue
        if bvid in cache:
            v["tname"] = cache[bvid].get("tname", v.get("tname", ""))
            v["tags"] = cache[bvid].get("tags", v.get("tags", []))
        else:
            need_fetch.append(v)

    if not need_fetch:
        print(f"==> 全部 {len(videos)} 个视频已有缓存, 无需补充")
        return

    print(f"==> 需要补充 {len(need_fetch)} 个视频的标签/分区...")

    ok = 0
    for i, v in enumerate(need_fetch):
        bvid = v.get("bvid", "")
        meta = _fetch_video_meta(bvid, session)
        if meta:
            cache[bvid] = meta
            v["tname"] = meta.get("tname", v.get("tname", ""))
            v["tags"] = meta.get("tags", v.get("tags", []))
            ok += 1
        if (i + 1) % 20 == 0:
            print(f"    进度: {i + 1}/{len(need_fetch)} (命中 {ok})")
        time.sleep(0.5)

    if ok == 0:
        print("==> 没有新数据需要保存")
        return

    cache_path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    FAVS_JSON.write_text(
        json.dumps(favs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"==> 补充完成: {ok}/{len(need_fetch)} 个视频获取到标签/分区")
    print(f"==> 缓存已保存到 {cache_path}")

    tname_counts: dict[str, int] = defaultdict(int)
    for v in videos:
        if v.get("tname"):
            tname_counts[v["tname"]] += 1
    if tname_counts:
        print("\n==> 分区分布:")
        for name, cnt in sorted(tname_counts.items(), key=lambda x: -x[1]):
            print(f"    {name}: {cnt}")

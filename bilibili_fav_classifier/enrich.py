"""Enrich video metadata: fetch tags and partition (tname) via video detail API.

Uses file-based cache (enrich_cache.json) to avoid re-fetching.
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

from bilibili_fav_classifier.config import (
    API_BASE,
    ENRICH_CACHE_JSON,
    FAVS_JSON,
)
from bilibili_fav_classifier.session import Session


def _fetch_video_meta(bvid: str, http) -> dict:
    """Fetch video detail to get tname (partition) and tags.

    Args:
        bvid: Video BVID.
        http: HttpClient instance (from session.http()).
    """
    try:
        r = http.get(f"{API_BASE}/x/web-interface/view?bvid={bvid}")
        j = r
        if j.get("code") != 0:
            return {}
        data = j.get("data", {})
        tags = [t.get("tag_name", "") for t in data.get("tags", [])]
        return {"tname": data.get("tname", ""), "tags": tags}
    except Exception as exc:
        print(f"    [warn] 获取 {bvid} 元数据失败: {exc}")
        return {}


def enrich_meta(
    session=None,
    favs_path=None,
    cache_path=None,
    progress_cb=None,
) -> None:
    """Supplement tname and tags for each video by calling the video detail API.

    Args:
        session: Authenticated Session. If None, loads from disk.
        favs_path: Path to favs.json. Defaults to config.FAVS_JSON.
        cache_path: Path to enrich_cache.json. Defaults to config.ENRICH_CACHE_JSON.
        progress_cb: Optional callback(pct, msg, detail) for progress updates.
    """
    if session is None:
        session = Session.load()

    http = session.http()

    if favs_path is None:
        favs_path = FAVS_JSON
    if cache_path is None:
        cache_path = ENRICH_CACHE_JSON

    favs_path = Path(favs_path)
    cache_path = Path(cache_path)

    if not favs_path.exists():
        print("==> 请先运行 collect")
        return

    cache: dict[str, dict] = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"警告: 缓存文件损坏 ({exc})，将重新获取全部标签")

    try:
        favs = json.loads(favs_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"错误: 收藏夹数据文件损坏: {exc}")
        return
    videos = favs.get("videos", [])

    need_fetch = []
    no_bvid = 0
    for v in videos:
        bvid = v.get("bvid", "")
        if not bvid:
            no_bvid += 1
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
    total = len(need_fetch)
    for i, v in enumerate(need_fetch):
        bvid = v.get("bvid", "")
        meta = _fetch_video_meta(bvid, http)
        if meta:
            cache[bvid] = meta
            v["tname"] = meta.get("tname", v.get("tname", ""))
            v["tags"] = meta.get("tags", v.get("tags", []))
            ok += 1
        if (i + 1) % 20 == 0:
            print(f"    进度: {i + 1}/{total} (命中 {ok})")
        if progress_cb:
            pct = int((i + 1) / total * 100) if total > 0 else 100
            progress_cb(pct, "补充标签...", f"{i + 1}/{total}  (命中 {ok})")
        time.sleep(0.5)

    if ok == 0:
        print("==> 没有新数据需要保存")
        return

    cache_path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    favs_path.write_text(
        json.dumps(favs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"==> 补充完成: {ok}/{len(need_fetch)} 个视频获取到标签/分区")
    print(f"==> 缓存已保存到 {cache_path}")
    if no_bvid:
        print(f"⚠ 跳过 {no_bvid} 个无 bvid 的视频")

    tname_counts: dict[str, int] = defaultdict(int)
    for v in videos:
        if v.get("tname"):
            tname_counts[v["tname"]] += 1
    if tname_counts:
        print("\n==> 分区分布:")
        for name, cnt in sorted(tname_counts.items(), key=lambda x: -x[1]):
            print(f"    {name}: {cnt}")

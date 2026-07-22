"""Classification orchestration: classify_video, autoclassify, genplan.

Pure logic — no CLI, no I/O orchestration beyond reading favs.json and writing plan.json.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from bilibili_fav_classifier.config import (
    AUTO_CLASSIFY_JSON,
    FAVS_JSON,
    PLAN_JSON,
)
from bilibili_fav_classifier.mappings import load_seed_mappings
from bilibili_fav_classifier.rules import (
    keyword_classify,
    partition_match,
    tag_match,
)


def classify_video(video: dict, up_to_folder: dict[str, str]) -> tuple[str, str]:
    """Classify a single video using four layers.

    Returns (folder, layer_name) where layer_name is one of:
    "tag", "partition", "up", "keyword", "fallback".
    """
    tags = video.get("tags") or []
    tname = video.get("tname", "")
    upper = video.get("upper") or ""

    result = tag_match(tags)
    if result:
        return result, "tag"

    result = partition_match(tname)
    if result:
        return result, "partition"

    if upper in up_to_folder:
        return up_to_folder[upper], "up"

    result = keyword_classify(video.get("title", ""))
    if result:
        return result, "keyword"

    return "其他", "fallback"


def autoclassify():
    """Classify all videos using 4-layer matching, write plan.json."""
    if not FAVS_JSON.exists():
        print("==> 请先运行 collect（和可选的 enrich_meta）")
        return

    favs = json.loads(FAVS_JSON.read_text(encoding="utf-8"))
    seed_map = load_seed_mappings()

    up_to_folder: dict[str, str] = {}
    for folder, ups in seed_map.items():
        for up in ups:
            up_to_folder[up] = folder

    groups: dict[str, list[dict]] = defaultdict(list)
    unmatched_ups: dict[str, list[str]] = {}
    layer_counts: dict[str, int] = defaultdict(int)

    for v in favs.get("videos", []):
        folder, layer = classify_video(v, up_to_folder)
        groups[folder].append(v)
        layer_counts[layer] += 1

        if layer == "fallback":
            upper_key = v.get("upper") or "未知UP"
            unmatched_ups.setdefault(upper_key, [])
            unmatched_ups[upper_key].append(v.get("title", ""))

    if unmatched_ups:
        AUTO_CLASSIFY_JSON.write_text(
            json.dumps(unmatched_ups, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"==> 未匹配UP ({len(unmatched_ups)} 个) 已保存到 auto_classified.json")

    plan = {
        "move": True,
        "groups": {
            folder: [{"id": v.get("id"), "bvid": v.get("bvid")} for v in vids]
            for folder, vids in groups.items()
        },
    }
    PLAN_JSON.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(len(v) for v in groups.values())
    print(f"\n==> 已生成 {PLAN_JSON}: {len(groups)} 个文件夹, 共 {total} 个视频")
    print(f"\n==> 分类命中统计:")
    print(f"    标签匹配:    {layer_counts.get('tag', 0)}")
    print(f"    分区匹配:    {layer_counts.get('partition', 0)}")
    print(f"    UP主映射:    {layer_counts.get('up', 0)}")
    print(f"    关键词匹配:  {layer_counts.get('keyword', 0)}")
    print(f"    归入'其他':  {len(unmatched_ups)} 个UP主")
    print()
    for f, vids in sorted(groups.items(), key=lambda x: -len(x[1])):
        print(f"    - {f}: {len(vids)}")
    if unmatched_ups:
        sample = list(unmatched_ups.keys())[:10]
        suffix = "..." if len(unmatched_ups) > 10 else ""
        print(f"\n==> 归入'其他'的UP主: {sample}{suffix}")
        print(f"    (在 seed_mappings.json 中添加映射可减少'其他')")
    print("\n==> 请检查 plan.json, 确认后运行 apply")


def genplan():
    """Simpler plan — manual UP mapping only, no keyword/tag/partition fallback."""
    if not FAVS_JSON.exists():
        print("==> 请先运行 collect")
        return

    favs = json.loads(FAVS_JSON.read_text(encoding="utf-8"))
    seed_map = load_seed_mappings()

    up_to_folder: dict[str, str] = {}
    for folder, ups in seed_map.items():
        for up in ups:
            up_to_folder[up] = folder

    groups: dict[str, list[dict]] = defaultdict(list)
    unmatched = set()
    for v in favs.get("videos", []):
        up = v.get("upper") or "未知UP"
        bvid = v.get("bvid") or ""
        vid = v.get("id") or bvid
        folder = up_to_folder.get(up)
        if folder:
            groups[folder].append({"bvid": bvid, "id": vid})
        else:
            unmatched.add(up)
            groups.setdefault("其他", []).append({"bvid": bvid, "id": vid})

    plan = {"move": True, "groups": dict(groups)}
    PLAN_JSON.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(len(v) for v in groups.values())
    print(f"==> 已生成 {PLAN_JSON}: {len(groups)} 个文件夹, 共 {total} 个视频")
    for f, bvs in groups.items():
        print(f"    - {f}: {len(bvs)}")
    if unmatched:
        sample = sorted(unmatched)[:20]
        suffix = "..." if len(unmatched) > 20 else ""
        print(f"==> 未匹配UP主 ({len(unmatched)}): {sample}{suffix}")
    print("==> 请检查 plan.json, 确认后运行 apply")

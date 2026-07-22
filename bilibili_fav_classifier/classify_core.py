"""Classification orchestration: classify_video, autoclassify, genplan.

Pure logic — no CLI, no file I/O. Callers provide data and receive results.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass, field

from bilibili_fav_classifier.rules import (
    keyword_classify,
    partition_match,
    tag_match,
)


@dataclass
class ClassifyResult:
    """Result of autoclassify — contains all data needed for output."""
    groups: dict[str, list[dict]] = field(default_factory=dict)
    layer_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    unmatched_ups: dict[str, list[str]] = field(default_factory=dict)
    total: int = 0


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


def autoclassify(
    favs_data: dict,
    seed_map: dict[str, list[str]],
) -> ClassifyResult:
    """Classify all videos using 4-layer matching.

    Args:
        favs_data: Parsed favs.json content (must have "videos" key).
        seed_map: UP主 → folder mapping from seed_mappings.json.

    Returns:
        ClassifyResult with groups, layer_counts, unmatched_ups, total.
    """
    up_to_folder: dict[str, str] = {}
    for folder, ups in seed_map.items():
        for up in ups:
            up_to_folder[up] = folder

    groups: dict[str, list[dict]] = defaultdict(list)
    unmatched_ups: dict[str, list[str]] = {}
    layer_counts: dict[str, int] = defaultdict(int)

    for v in favs_data.get("videos", []):
        folder, layer = classify_video(v, up_to_folder)
        groups[folder].append(v)
        layer_counts[layer] += 1

        if layer == "fallback":
            upper_key = v.get("upper") or "未知UP"
            unmatched_ups.setdefault(upper_key, [])
            unmatched_ups[upper_key].append(v.get("title", ""))

    total = sum(len(v) for v in groups.values())
    return ClassifyResult(
        groups=dict(groups),
        layer_counts=dict(layer_counts),
        unmatched_ups=unmatched_ups,
        total=total,
    )


def genplan(
    favs_data: dict,
    seed_map: dict[str, list[str]],
) -> dict:
    """Generate a simple plan using only UP主 mapping.

    Args:
        favs_data: Parsed favs.json content (must have "videos" key).
        seed_map: UP主 → folder mapping from seed_mappings.json.

    Returns:
        Plan dict: {"move": True, "groups": {folder: [{"id": ..., "bvid": ...}]}}
    """
    up_to_folder: dict[str, str] = {}
    for folder, ups in seed_map.items():
        for up in ups:
            up_to_folder[up] = folder

    groups: dict[str, list[dict]] = defaultdict(list)
    for v in favs_data.get("videos", []):
        up = v.get("upper") or "未知UP"
        bvid = v.get("bvid") or ""
        vid = v.get("id") or bvid
        folder = up_to_folder.get(up)
        if folder:
            groups[folder].append({"bvid": bvid, "id": vid})
        else:
            groups.setdefault("其他", []).append({"bvid": bvid, "id": vid})

    return {"move": True, "groups": dict(groups)}

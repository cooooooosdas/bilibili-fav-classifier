"""Classification orchestration: classify_video, autoclassify.

Pure logic — no CLI, no file I/O. Callers provide data and receive results.
"""
from __future__ import annotations

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
    duplicate_ups: dict[str, list[str]] = field(default_factory=dict)  # UP主 -> 多文件夹
    total: int = 0


def classify_video(video: dict, up_to_folder: dict[str, str]) -> tuple[str, str]:
    """Classify a single video using four layers.

    Priority: UP mapping > tag > partition > keyword > "其他"
    - UP mapping: user's manual preference (most reliable)
    - tag: user-added Bilibili tags (per-video signal)
    - partition: Bilibili official category (structural)
    - keyword: title keywords (fallback inference)

    Returns (folder, layer_name) where layer_name is one of:
    "up", "tag", "partition", "keyword", "fallback".
    """
    upper = video.get("upper") or ""

    # Layer 1: UP主 mapping (highest priority - user's explicit preference)
    if upper in up_to_folder:
        return up_to_folder[upper], "up"

    # Layer 2: tag matching
    tags = video.get("tags")
    result = tag_match(tags)
    if result:
        return result, "tag"

    # Layer 3: partition matching
    tname = video.get("tname", "")
    result = partition_match(tname)
    if result:
        return result, "partition"

    # Layer 4: keyword matching (title inference)
    result = keyword_classify(video.get("title", ""))
    if result:
        return result, "keyword"

    # Layer 5: fallback
    return "其他", "fallback"


def autoclassify(
    favs_data: dict,
    seed_map: dict[str, list[str]],
) -> ClassifyResult:
    """Classify all videos using 4-layer matching with UP priority.

    UP主 mapping has highest priority. Duplicate UP→multiple-folders
    are detected and reported as warnings.

    Args:
        favs_data: Parsed favs.json content (must have "videos" key).
        seed_map: UP主 → folder mapping from seed_mappings.json.

    Returns:
        ClassifyResult with groups, layer_counts, unmatched_ups,
        duplicate_ups, total.
    """
    up_to_folder: dict[str, str] = {}
    # Detect duplicate UP mappings: a UP mapped to multiple folders
    up_folder_counts: dict[str, int] = defaultdict(int)
    for folder, ups in seed_map.items():
        for up in ups:
            up_folder_counts[up] += 1
            # Keep last mapping (consistent with JSON order)
            up_to_folder[up] = folder

    duplicate_ups = {up: [] for up, cnt in up_folder_counts.items() if cnt > 1}

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
        duplicate_ups=duplicate_ups,
        total=total,
    )

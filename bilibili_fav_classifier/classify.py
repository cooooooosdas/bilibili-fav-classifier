"""CLI entry point for bilibili-fav-classifier.

Pipeline: collect → enrich_meta → autoclassify → apply
"""
from __future__ import annotations

import asyncio
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from bilibili_fav_classifier.classify_core import ClassifyResult, autoclassify, genplan
from bilibili_fav_classifier.collect import collect as _collect
from bilibili_fav_classifier.config import (
    AUTO_CLASSIFY_JSON,
    ENRICH_CACHE_JSON,
    FAVS_JSON,
    PLAN_JSON,
    load_user_config,
)
from bilibili_fav_classifier.enrich import enrich_meta
from bilibili_fav_classifier.mappings import load_seed_mappings
from bilibili_fav_classifier.session import Session


def _print_classify_result(result: ClassifyResult) -> None:
    """Print classification statistics from ClassifyResult."""
    print(f"\n==> 已生成 {PLAN_JSON}: {len(result.groups)} 个文件夹, 共 {result.total} 个视频")
    print(f"\n==> 分类命中统计:")
    print(f"    标签匹配:    {result.layer_counts.get('tag', 0)}")
    print(f"    分区匹配:    {result.layer_counts.get('partition', 0)}")
    print(f"    UP主映射:    {result.layer_counts.get('up', 0)}")
    print(f"    关键词匹配:  {result.layer_counts.get('keyword', 0)}")
    print(f"    归入'其他':  {len(result.unmatched_ups)} 个UP主")
    print()
    for f, vids in sorted(result.groups.items(), key=lambda x: -len(x[1])):
        print(f"    - {f}: {len(vids)}")
    if result.unmatched_ups:
        sample = list(result.unmatched_ups.keys())[:10]
        suffix = "..." if len(result.unmatched_ups) > 10 else ""
        print(f"\n==> 归入'其他'的UP主: {sample}{suffix}")
        print(f"    (在 seed_mappings.json 中添加映射可减少'其他')")
    print("\n==> 请检查 plan.json, 确认后运行 apply")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    if cmd == "collect":
        asyncio.run(_collect())

    elif cmd == "enrich_meta":
        enrich_meta()

    elif cmd == "autoclassify":
        if not FAVS_JSON.exists():
            print("==> 请先运行 collect（和可选的 enrich_meta）")
            return
        favs = json.loads(FAVS_JSON.read_text(encoding="utf-8"))
        seed_map = load_seed_mappings()
        result = autoclassify(favs, seed_map)

        if result.unmatched_ups:
            AUTO_CLASSIFY_JSON.write_text(
                json.dumps(result.unmatched_ups, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"==> 未匹配UP ({len(result.unmatched_ups)} 个) 已保存到 auto_classified.json")

        plan = {
            "move": True,
            "groups": {
                folder: [{"id": v.get("id"), "bvid": v.get("bvid")} for v in vids]
                for folder, vids in result.groups.items()
            },
        }
        PLAN_JSON.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        _print_classify_result(result)

    elif cmd == "genplan":
        if not FAVS_JSON.exists():
            print("==> 请先运行 collect")
            return
        favs = json.loads(FAVS_JSON.read_text(encoding="utf-8"))
        seed_map = load_seed_mappings()
        plan = genplan(favs, seed_map)
        PLAN_JSON.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

        total = sum(len(v) for v in plan.get("groups", {}).values())
        print(f"==> 已生成 {PLAN_JSON}: {len(plan.get('groups', {}))} 个文件夹, 共 {total} 个视频")
        for f, bvs in plan.get("groups", {}).items():
            print(f"    - {f}: {len(bvs)}")
        unmatched = {
            up for ups in seed_map.values() for up in ups
            if up not in {v.get("upper") for v in favs.get("videos", [])}
        }
        if unmatched:
            sample = sorted(unmatched)[:20]
            suffix = "..." if len(unmatched) > 20 else ""
            print(f"==> 未匹配UP主 ({len(unmatched)}): {sample}{suffix}")
        print("==> 请检查 plan.json, 确认后运行 apply")

    elif cmd == "apply":
        session = Session.load()
        csrf = session.csrf
        from bilibili_fav_classifier.apply import apply as _apply
        _apply(session.http(), csrf, sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

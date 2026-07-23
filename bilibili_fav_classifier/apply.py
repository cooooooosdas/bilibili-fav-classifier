"""Apply classification plan: create folders and move videos.

Uses injectable HTTP client (from session module) for testability.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from bilibili_fav_classifier.config import (
    API_BASE,
    APPLY_LOG_JSON,
    BATCH_SIZE,
    PLAN_JSON,
)
from bilibili_fav_classifier.session import HttpClient


def _load_folders(http: HttpClient, user_mid: str, default_fav_id: int) -> tuple[dict[str, int], int]:
    """Return (name_to_id, default_id) from Bilibili API."""
    data = http.get(
        f"{API_BASE}/x/v3/fav/folder/created/list-all"
        f"?up_mid={user_mid}&platform=web"
    )
    folders = data.get("data", {}).get("list", [])
    name_to_id = {f.get("title"): f.get("id") for f in folders if f.get("id")}
    default = next(
        (f for f in folders if "默认" in (f.get("title") or "")), None
    )
    default_id = default.get("id") if default else default_fav_id
    return name_to_id, default_id


def _batch_move(
    http: HttpClient, csrf: str, user_mid: str,
    src_media_id: int | str, tar_media_id: int | str,
    resources: list[str],
) -> dict:
    """Batch move videos via /x/v3/fav/resource/move API."""
    data = {
        "resources": ",".join(f"{r}:2" for r in resources),
        "src_media_id": str(src_media_id),
        "tar_media_id": str(tar_media_id),
        "mid": user_mid,
        "platform": "web",
        "csrf": csrf,
    }
    return http.post(f"{API_BASE}/x/v3/fav/resource/move", data)


def apply(
    http: HttpClient, csrf: str,
    user_mid: str = "", default_fav_id: int = 0,
    only_folder: str | None = None,
    plan_path=None,
    log_path=None,
    progress_cb=None,
) -> None:
    """Execute the classification plan: create folders and move videos.

    Args:
        http: Injected HTTP client (swap for tests).
        csrf: CSRF token from cookies.
        user_mid: User's Bilibili MID.
        default_fav_id: Default favorite folder ID.
        only_folder: If set, only process this folder.
        plan_path: Override plan.json path (for testing).
        log_path: Override apply_log.json path (for testing).
        progress_cb: Optional callback(pct, msg, detail) for progress updates.
    """
    plan_file = Path(plan_path) if plan_path is not None else PLAN_JSON
    if not plan_file.exists():
        print(f"未找到 {plan_file}, 请先 collect 并生成 plan.json")
        return

    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    if not isinstance(plan, dict):
        print(f"错误: {plan_file} 格式不正确")
        return
    do_move = plan.get("move", True)
    groups = plan.get("groups", {})
    if not isinstance(groups, dict):
        print("错误: plan.json['groups'] 格式不正确")
        return
    total = sum(len(v) for v in groups.values())
    print(f"==> 计划: {len(groups)} 个文件夹, 共 {total} 个视频, move={do_move}")

    name_to_id, default_id = _load_folders(http, user_mid, default_fav_id)
    log: list[dict] = []
    CREATE_URL = f"{API_BASE}/x/v3/fav/folder/add"

    for folder_name, bvids in groups.items():
        if only_folder and folder_name != only_folder:
            continue
        if folder_name == "其他":
            print(f"\n==> 跳过 '其他' (共 {len(bvids)} 个)")
            log.append({"folder": folder_name, "skipped": True, "count": len(bvids)})
            continue

        if folder_name in name_to_id:
            fid = name_to_id[folder_name]
            print(f"\n==> 收藏夹已存在: {folder_name} (id={fid})")
        else:
            print(f"\n==> 创建收藏夹: {folder_name}")
            if progress_cb:
                progress_cb(5, "创建收藏夹...", folder_name)
            r = http.post(CREATE_URL, {
                "title": folder_name, "intro": "", "privacy": 0, "cover": "", "csrf": csrf,
            })
            if r.get("code") != 0:
                print(f"    创建失败: {r}")
                log.append({"folder": folder_name, "error": "create failed", "resp": r})
                continue
            fid = r.get("data", {}).get("id")
            name_to_id[folder_name] = fid
            print(f"    创建成功 id={fid}")
            if progress_cb:
                progress_cb(10, "收藏夹已创建", folder_name)
            time.sleep(2)

        ok = fail = 0
        total_vids = len(bvids)

        if do_move:
            if progress_cb:
                progress_cb(15, "移动视频...", f"{folder_name} ({total_vids} 个)")
            for batch_start in range(0, total_vids, BATCH_SIZE):
                batch = bvids[batch_start:batch_start + BATCH_SIZE]
                rids = [str(v.get("id") or v.get("bvid", "")) for v in batch]
                if progress_cb:
                    batch_pct = 15 + int(batch_start / total_vids * 70) if total_vids else 15
                    progress_cb(batch_pct, "移动视频...", f"{folder_name}: {batch_start}/{total_vids}")
                result = _batch_move(http, csrf, user_mid, default_id, fid, rids)

                if result.get("_waf_html"):
                    print(
                        f"    [{folder_name}] 批次 {batch_start // BATCH_SIZE + 1}"
                        f" WAF限流, 冷却60秒...",
                        flush=True,
                    )
                    time.sleep(60)
                    result = _batch_move(http, csrf, user_mid, default_id, fid, rids)
                    if result.get("_waf_html"):
                        print(
                            f"    [{folder_name}] 批次 {batch_start // BATCH_SIZE + 1}"
                            f" 冷却后仍限流, 跳过",
                            flush=True,
                        )
                        fail += len(batch)
                        continue

                code = result.get("code", -1)
                if code == 0:
                    ok += len(batch)
                    print(
                        f"    [{folder_name}] 批次 {batch_start // BATCH_SIZE + 1}"
                        f": {len(batch)}/{len(batch)} (累计 {ok}/{total_vids})",
                        flush=True,
                    )
                else:
                    print(
                        f"    [{folder_name}] 批次 {batch_start // BATCH_SIZE + 1}"
                        f": 失败 code={code} {str(result.get('message', ''))[:60]}",
                        flush=True,
                    )
                    fail += len(batch)
                    log.append({"folder": folder_name, "batch": batch_start, "error": result})

                time.sleep(1.5)
        else:
            if progress_cb:
                progress_cb(15, "预览模式...", f"{folder_name} ({total_vids} 个)")
            for batch_start in range(0, total_vids, BATCH_SIZE):
                batch = bvids[batch_start:batch_start + BATCH_SIZE]
                rids = [str(v.get("id") or v.get("bvid", "")) for v in batch]
                result = _batch_move(http, csrf, user_mid, 0, fid, rids)
                code = result.get("code", -1)
                if code == 0:
                    ok += len(batch)
                else:
                    fail += len(batch)
                print(
                    f"    [{folder_name}] 批次 {batch_start // BATCH_SIZE + 1}"
                    f": {'OK' if code == 0 else 'FAIL'} ({ok}/{total_vids})",
                    flush=True,
                )
                time.sleep(1.5)

        print(f"==> {folder_name}: 移动 {ok}/{total_vids} 成功 (失败{fail})")
        if progress_cb:
            progress_cb(85, "移动视频...", f"{folder_name}: {ok}/{total_vids}")
        log.append({
            "folder": folder_name, "id": fid,
            "moved": ok, "total": total_vids, "failed": fail,
        })
        time.sleep(2)

    log_file = Path(log_path) if log_path is not None else APPLY_LOG_JSON
    log_file.write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    total_ok = sum(e.get("moved", 0) for e in log if isinstance(e, dict) and "moved" in e)
    total_fail = sum(e.get("failed", 0) for e in log if isinstance(e, dict) and "failed" in e)
    print(f"\n==> 完成! 日志: {log_file}")
    print(f"==> 总计移动: {total_ok}/{total} 个视频 (失败 {total_fail})")

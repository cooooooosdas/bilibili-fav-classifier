"""B站收藏夹智能分类工具 — 三阶段流程:

  1. collect    — 拉取默认收藏夹的全部视频, 保存到 favs.json
  2. autoclassify — 自动分类 (手动映射 + 关键词匹配), 生成 plan.json
  3. apply      — 创建收藏夹并移动视频

Usage:
  python -m bilibili_fav_classifier collect
  python -m bilibili_fav_classifier autoclassify
  python -m bilibili_fav_classifier apply
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from playwright.async_api import async_playwright

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from bilibili_fav_classifier.config import (
    API_BASE,
    APPLY_LOG_JSON,
    BATCH_SIZE,
    COOKIES_PATH,
    DEFAULT_FAV_ID,
    FAVS_JSON,
    MANUAL_MAP_JSON,
    PLAN_JSON,
    USER_MID,
)
from bilibili_fav_classifier.mappings import load_mappings

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


# ──────────────────────── Cookie helpers ────────────────────────


async def save_cookies(context):
    cookies = await context.cookies()
    COOKIES_PATH.write_text(
        json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"==> 已保存 {len(cookies)} 个 cookies 到 {COOKIES_PATH}")


async def load_cookies(context):
    if not COOKIES_PATH.exists():
        return False
    cookies = json.loads(COOKIES_PATH.read_text(encoding="utf-8"))
    await context.add_cookies(cookies)
    return True


async def wait_for_login(page, timeout: int = 180):
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


# ──────────────────────── Collect ────────────────────────


async def collect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            executable_path=CHROME_PATH,
            args=BROWSER_ARGS,
        )
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(
            f"https://space.bilibili.com/{USER_MID}/favlist"
            f"?fid={DEFAULT_FAV_ID}",
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
                if (j.code !== 0) {{ all.push({{error: true, code: j.code, page: pn}}); break; }}
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

        # Generate UP summary for manual mapping
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
        print("==> 下一步: 运行 autoclassify 自动分类, 再运行 apply")
        await context.close()
        await browser.close()


# ──────────────────────── API helpers ────────────────────────


def _post_via_page(page, url: str, data: dict, csrf: str, retries: int = 3):
    if csrf:
        data["csrf"] = csrf
    js = """async ([url, data, retries]) => {
        const toForm = (d) => {
            const p = new URLSearchParams();
            for (const k in d) {
                const v = d[k];
                if (Array.isArray(v)) v.forEach(x => p.append(k, x));
                else p.append(k, v);
            }
            return p;
        };
        const body = toForm(data);
        for (let i = 0; i < retries; i++) {
            try {
                const r = await fetch(url, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'},
                    credentials: 'include',
                    body,
                });
                const ct = r.headers.get('content-type') || '';
                if (!ct.includes('json')) return {_error: true, _status: r.status, _ctype: ct};
                const j = await r.json();
                if (j.code === -999 || j.code === -101)
                    return {_error: true, _status: r.status, _code: j.code};
                return j;
            } catch (e) {
                if (i === retries - 1) return {_error: true, _msg: e.message};
                await new Promise(r => setTimeout(r, 800));
            }
        }
    }"""
    result = await page.evaluate(js, [url, data, retries])
    if result and result.get("_error"):
        raise RuntimeError(
            f"API error: status={result.get('_status')}"
            f" code={result.get('_code')} ctype={result.get('_ctype')}"
            f" msg={result.get('_msg')}"
        )
    return result


async def create_folder(page, title: str, csrf: str):
    return await _post_via_page(
        page, f"{API_BASE}/x/v3/fav/folder/add",
        {"title": title, "intro": "", "privacy": 0, "cover": ""},
        csrf,
    )


# ──────────────────────── Classification rules ────────────────────────

KEYWORD_RULES: list[tuple[str, str]] = [
    (
        "编程/开发/技术/AI/代码/算法/Claude/Cursor/Coze/Agent"
        "/Python/Java/C++/前端/后端/框架/引擎/软件/程序"
        "/VSCode/Git/Linux/Docker/API/GitHub/程序员/后端/前端",
        "AI与编程技术",
    ),
    (
        "算法/竞赛/ACM/蓝桥杯/数模/建模/数学/高数/线代/概率"
        "/论文/科研/SCI/英语/四级/六级/CET/雅思/托福"
        "/考研/期末/复习/课件/物理/化学/生物/经管",
        "学习与竞赛",
    ),
    (
        "游戏/GTA/原神/三角洲/我的世界/实况/攻略/Steam"
        "/塞尔达/黑神话/王者/和平精英/实况/LOL/CSGO/MC",
        "游戏与动漫",
    ),
    (
        "动漫/新番/番剧/鬼灭/咒术/进击的巨人/间谍过家家/崩坏",
        "游戏与动漫",
    ),
    ("健身/跑步/减肥/运动/KEEP/肌肉/拉伸/瑜伽", "体育"),
    (
        "音乐/翻唱/钢琴/吉他/古筝/日文歌/歌词/NIGHT DANCER"
        "/歌曲/演唱/MV/BGM/纯音乐",
        "音乐",
    ),
    (
        "情感/文案/治愈/感悟/人生/爱情/故事/遗憾/告别"
        "/EMO/伤感/emo",
        "情感与文案",
    ),
    (
        "历史/二战/苏联/蒋介石/国民党/近代史/朝代"
        "/时政/国际/俄乌/特朗普/访华/地缘政治/资本家",
        "历史与时政",
    ),
    ("美食/做饭/食谱/探店/深夜食堂/厨师/烘焙", "生活与社会"),
    (
        "旅行/生活/日常/Vlog/大学生/毕业/职场/社畜"
        "/科普/知识/冷知识/科学/物理/化学/纪录片"
        "/影视/电影/解说/影评/Netflix/汽车/数码/测评"
        "/手机/电脑/硬件/搞笑/整活/鬼畜/沙雕/离谱",
        "生活与社会",
    ),
]


def keyword_classify(title: str) -> str | None:
    t = (title or "").lower()
    for keywords, folder in KEYWORD_RULES:
        for kw in keywords.split("/"):
            if kw.lower() in t:
                return folder
    return None


# ──────────────────────── Auto classify ────────────────────────


def autoclassify():
    if not FAVS_JSON.exists():
        print("==> 请先运行 collect")
        return

    favs = json.loads(FAVS_JSON.read_text(encoding="utf-8"))
    manual = load_mappings()

    # Flatten to up → folder lookup
    up_to_folder: dict[str, str] = {}
    for folder, ups in manual.items():
        for up in ups:
            up_to_folder[up] = folder

    # Group by uploader
    up_vids: dict[str, list[dict]] = defaultdict(list)
    for v in favs.get("videos", []):
        up = v.get("upper") or "未知UP"
        up_vids[up].append(v)

    groups: dict[str | None, list[dict]] = {}
    unmatched_ups: dict[str, list[str]] = {}

    for up, vids in up_vids.items():
        if up in up_to_folder:
            folder = up_to_folder[up]
        else:
            folder = None
            for v in vids:
                kf = keyword_classify(v.get("title", ""))
                if kf:
                    folder = kf
                    break
            if not folder:
                folder = "其他"
                unmatched_ups[up] = [v.get("title", "") for v in vids[:3]]
        groups.setdefault(folder, []).extend(vids)

    if unmatched_ups:
        AUTO_CLASSIFY_JSON.write_text(
            json.dumps(unmatched_ups, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            f"==> 未匹配UP ({len(unmatched_ups)} 个)"
            f" 已保存到 {AUTO_CLASSIFY_JSON}"
        )

    plan = {
        "move": True,
        "groups": {
            folder: [{"id": v.get("id"), "bvid": v.get("bvid")} for v in vids]
            for folder, vids in groups.items()
            if folder
        },
    }
    PLAN_JSON.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(len(v) for v in groups.values() if v)
    print(f"==> 已生成 {PLAN_JSON}: {len(groups)} 个文件夹, 共 {total} 个视频")
    for f, vids in sorted(groups.items(), key=lambda x: -len(x[1]) if x[1] else 0):
        print(f"    - {f or '(跳过)'}: {len(vids)}")
    if unmatched_ups:
        sample = list(unmatched_ups.keys())[:10]
        suffix = "..." if len(unmatched_ups) > 10 else ""
        print(f"==> 归入'其他'的UP主: {sample}{suffix}")
    print("==> 请检查 plan.json, 确认后运行 apply")


def genplan():
    """Simpler plan generator — manual mapping only, no keyword fallback."""
    if not FAVS_JSON.exists():
        print("==> 请先运行 collect")
        return

    favs = json.loads(FAVS_JSON.read_text(encoding="utf-8"))
    manual = load_mappings()

    up_to_folder: dict[str, str] = {}
    for folder, ups in manual.items():
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
        print(
            f"==> 未匹配UP主 ({len(unmatched)}), 已归入'其他': {sample}{suffix}"
        )
    print("==> 请检查 plan.json, 确认后运行 apply")


# ──────────────────────── Apply ────────────────────────


def _api_get(url: str, cookies: dict, headers: dict):
    r = requests.get(url, cookies=cookies, headers=headers, timeout=15)
    return r.json()


def _api_post(url: str, data: dict, cookies: dict, headers: dict):
    try:
        r = requests.post(url, data=data, cookies=cookies, headers=headers, timeout=15)
        ct = r.headers.get("content-type", "")
        if "json" not in ct.lower():
            return {"_waf_html": True, "_status": r.status_code, "_ctype": ct}
        return r.json()
    except requests.exceptions.JSONDecodeError:
        return {"_waf_html": True, "_error": "json_decode"}
    except Exception as e:
        return {"_error": True, "_msg": str(e)}


def _batch_move(
    cookies: dict, csrf: str, src_media_id: int | str,
    tar_media_id: int | str, resources: list[str],
) -> dict:
    """Batch move videos via /x/v3/fav/resource/move API."""
    headers = {
        "Referer": "https://www.bilibili.com/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    resources_str = ",".join(f"{r}:2" for r in resources)
    data = {
        "resources": resources_str,
        "src_media_id": str(src_media_id),
        "tar_media_id": str(tar_media_id),
        "mid": USER_MID,
        "platform": "web",
        "csrf": csrf,
    }
    r = requests.post(
        f"{API_BASE}/x/v3/fav/resource/move",
        data=data, cookies=cookies, headers=headers, timeout=30,
    )
    ct = r.headers.get("content-type", "")
    if "json" not in ct.lower():
        return {"_waf_html": True, "_status": r.status_code}
    return r.json()


def apply(only_folder: str | None = None):
    if not PLAN_JSON.exists():
        print(f"未找到 {PLAN_JSON}, 请先 collect 并生成 plan.json")
        return

    plan = json.loads(PLAN_JSON.read_text(encoding="utf-8"))
    do_move = plan.get("move", True)
    groups = plan.get("groups", {})
    total = sum(len(v) for v in groups.values())
    print(f"==> 计划: {len(groups)} 个文件夹, 共 {total} 个视频, move={do_move}")

    cookies_raw = json.loads(COOKIES_PATH.read_text(encoding="utf-8"))
    cookies = {c["name"]: c["value"] for c in cookies_raw}
    csrf = cookies.get("bili_jct", "")
    if not csrf:
        print("==> cookies 中无 bili_jct, 请重新运行 collect")
        return

    headers = {
        "Referer": "https://www.bilibili.com/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    folders_data = _api_get(
        f"{API_BASE}/x/v3/fav/folder/created/list-all"
        f"?up_mid={USER_MID}&platform=web",
        cookies, headers,
    )
    folders = folders_data.get("data", {}).get("list", [])
    name_to_id = {f.get("title"): f.get("id") for f in folders if f.get("id")}

    default = next(
        (f for f in folders if "默认" in (f.get("title") or "")), None
    )
    default_id = default.get("id") if default else DEFAULT_FAV_ID

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
            r = _api_post(
                CREATE_URL,
                {"title": folder_name, "intro": "", "privacy": 0, "cover": "", "csrf": csrf},
                cookies, headers,
            )
            if r.get("code") != 0:
                print(f"    创建失败: {r}")
                log.append({"folder": folder_name, "error": "create failed", "resp": r})
                continue
            fid = r.get("data", {}).get("id")
            name_to_id[folder_name] = fid
            print(f"    创建成功 id={fid}")
            time.sleep(2)

        ok = fail = 0
        total_vids = len(bvids)

        if do_move:
            for batch_start in range(0, total_vids, BATCH_SIZE):
                batch = bvids[batch_start:batch_start + BATCH_SIZE]
                rids = [str(v.get("id") or v.get("bvid", "")) for v in batch]

                result = _batch_move(cookies, csrf, default_id, fid, rids)

                if result.get("_waf_html"):
                    print(
                        f"    [{folder_name}] 批次 {batch_start // BATCH_SIZE + 1}"
                        f" WAF限流 (status={result.get('_status')}), 冷却60秒...",
                        flush=True,
                    )
                    time.sleep(60)
                    result = _batch_move(cookies, csrf, default_id, fid, rids)
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
                    batch_ok = len(batch)
                    ok += batch_ok
                    print(
                        f"    [{folder_name}] 批次 {batch_start // BATCH_SIZE + 1}"
                        f": {batch_ok}/{len(batch)} (累计 {ok}/{total_vids})",
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
            for batch_start in range(0, total_vids, BATCH_SIZE):
                batch = bvids[batch_start:batch_start + BATCH_SIZE]
                rids = [str(v.get("id") or v.get("bvid", "")) for v in batch]
                result = _batch_move(cookies, csrf, 0, fid, rids)
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
        log.append({
            "folder": folder_name,
            "id": fid,
            "moved": ok,
            "total": total_vids,
            "failed": fail,
        })
        time.sleep(2)

    APPLY_LOG_JSON.write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    total_ok = sum(e.get("moved", 0) for e in log if isinstance(e, dict) and "moved" in e)
    total_fail = sum(e.get("failed", 0) for e in log if isinstance(e, dict) and "failed" in e)
    print(f"\n==> 完成! 日志: {APPLY_LOG_JSON}")
    print(f"==> 总计移动: {total_ok}/{total} 个视频 (失败 {total_fail})")


# ──────────────────────── CLI ────────────────────────


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    if cmd == "collect":
        asyncio.run(collect())
    elif cmd == "autoclassify":
        autoclassify()
    elif cmd == "genplan":
        genplan()
    elif cmd == "apply":
        apply(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

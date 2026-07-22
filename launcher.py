"""One-click launcher GUI for bilibili-fav-classifier.

Pipeline: collect → enrich → classify → apply
Works as a Python script or a PyInstaller-frozen .exe.
"""
from __future__ import annotations

import asyncio
import json
import os
import queue
import sys
import threading
from pathlib import Path

import PySimpleGUI as sg

from bilibili_fav_classifier.apply import apply
from bilibili_fav_classifier.classify_core import autoclassify
from bilibili_fav_classifier.collect import collect
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


# ─── Helpers ──────────────────────────────────────────────────────

def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _base_dir() -> Path:
    """Directory containing the exe (frozen) or launcher.py (dev)."""
    if _is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).parent


def _setup_frozen_env():
    """Set environment variables for frozen builds."""
    if not _is_frozen():
        return
    browsers_path = _base_dir() / "ms-playwright"
    if browsers_path.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)


def _check_browsers() -> bool:
    """Quick check if Playwright can launch Chromium."""
    if _is_frozen():
        browsers_path = _base_dir() / "ms-playwright"
        if not browsers_path.is_dir():
            return False
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        return True
    except Exception:
        return False


# ─── Pipeline Runner ──────────────────────────────────────────────

class PipelineRunner:
    """Execute the pipeline in a background thread, push logs to a queue."""

    def __init__(self, log_q: queue.Queue, progress_cb):
        self.q = log_q
        self.progress = progress_cb
        self._stop = threading.Event()

    def log(self, msg: str):
        self.q.put(("log", msg))

    def stop(self):
        self._stop.set()

    def run(self):
        try:
            self._collect()
            if self._stop.is_set():
                return self._done()
            self._enrich()
            if self._stop.is_set():
                return self._done()
            self._classify()
            if self._stop.is_set():
                return self._done()
            self._apply()
            self._done()
        except Exception as exc:
            self.log(f"\n❌ 错误: {exc}")
            import traceback

            self.log(traceback.format_exc())
            self.q.put(("error", str(exc)))

    def _collect(self):
        self.log("━" * 50)
        self.log("步骤 1/4: 扫码登录并拉取收藏夹")
        self.progress(5, "启动浏览器...")

        import bilibili_fav_classifier.collect as collect_mod

        original_path = collect_mod.CHROME_PATH
        bundled = _find_bundled_browser()
        if bundled:
            collect_mod.CHROME_PATH = bundled

        try:
            asyncio.run(collect())
        finally:
            collect_mod.CHROME_PATH = original_path

        if self._stop.is_set():
            return
        if not FAVS_JSON.exists():
            self.log("❌ 收藏夹数据未生成")
            return

        favs = json.loads(FAVS_JSON.read_text(encoding="utf-8"))
        self.log(f"✓ 已拉取 {favs.get('count', 0)} 个视频")

        cfg = load_user_config()
        self.log(f"✓ MID: {cfg.get('USER_MID', '?')}")
        self.log(f"✓ 默认收藏夹 ID: {cfg.get('DEFAULT_FAV_ID', '?')}")
        self.progress(25, "收藏夹拉取完成")

    def _enrich(self):
        self.log("━" * 50)
        self.log("步骤 2/4: 补充视频标签和分区")
        self.progress(30, "分析视频元数据...")
        session = Session.load()
        enrich_meta(session=session)
        self.progress(50, "标签补充完成")
        self.log("✓ 标签/分区补充完成")

    def _classify(self):
        self.log("━" * 50)
        self.log("步骤 3/4: 智能分类")
        self.progress(55, "分析分类...")

        favs = json.loads(FAVS_JSON.read_text(encoding="utf-8"))
        seed_map = load_seed_mappings()
        result = autoclassify(favs, seed_map)

        plan = {
            "move": True,
            "groups": {
                folder: [
                    {"id": v.get("id"), "bvid": v.get("bvid")} for v in vids
                ]
                for folder, vids in result.groups.items()
            },
        }
        PLAN_JSON.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if result.unmatched_ups:
            AUTO_CLASSIFY_JSON.write_text(
                json.dumps(result.unmatched_ups, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        self.progress(75, "分类完成")
        self.log(f"✓ {result.total} 个视频 → {len(result.groups)} 个文件夹")
        for folder, vids in sorted(result.groups.items(), key=lambda x: -len(x[1])):
            self.log(f"    {folder}: {len(vids)}")
        if result.unmatched_ups:
            self.log(
                f"⚠ '其他'包含 {len(result.unmatched_ups)} 个UP主"
                " (可编辑 seed_mappings.json 优化)"
            )

    def _apply(self):
        self.log("━" * 50)
        self.log("步骤 4/4: 应用分类计划")
        self.progress(80, "执行分类...")
        session = Session.load()
        apply(session.http(), session.csrf)
        self.progress(100, "全部完成!")
        self.log("━" * 50)
        self.log("\U0001f389 全部完成!")

    def _done(self):
        self.q.put(("done", None))


def _find_bundled_browser() -> str | None:
    """Find Chromium executable in bundled Playwright browsers dir."""
    browsers_dir = _base_dir() / "ms-playwright"
    if not browsers_dir.is_dir():
        return None
    for root, _dirs, files in os.walk(browsers_dir):
        for fname in files:
            if fname in ("chrome.exe", "chromium.exe"):
                return os.path.join(root, fname)
    return None


# ─── GUI ──────────────────────────────────────────────────────────

THEME = "LightBlue3"


def _build_layout():
    header = [
        [
            sg.Text(
                "B站收藏夹智能分类",
                font=("Microsoft YaHei", 16, "bold"),
                pad=(10, 15),
                expand_x=True,
                justification="center",
            )
        ],
    ]
    status_row = [
        [
            sg.Text("就绪", key="-STATUS-", size=(50, 1), font=("Microsoft YaHei", 10)),
        ],
    ]
    progress_row = [
        [sg.ProgressBar(100, size=(60, 18), key="-PROG-")],
    ]
    log_frame = [
        [
            sg.Multiline(
                size=(80, 22),
                key="-LOG-",
                autoscroll=True,
                disabled=True,
                font=("Consolas", 9),
                text_color="#333",
                background_color="#f7f7f7",
                border_width=1,
                
                pad=(5, 5),
            )
        ],
    ]
    buttons = [
        sg.Button(
            "▶ 开始一键分类",
            key="-START-",
            size=(14, 2),
            button_color=("white", "#4CAF50"),
            font=("Microsoft YaHei", 10),
        ),
        sg.Button("⏹ 停止", key="-STOP-", disabled=True, size=(8, 1)),
        sg.Button("\U0001f4c2 打开数据文件夹", key="-OPEN-", size=(16, 1)),
    ]
    footer = [
        [
            sg.Text(
                "数据仅存储在本地，不会上传到任何服务器",
                font=("Microsoft YaHei", 8),
                text_color="gray",
                pad=(10, 5),
            )
        ],
    ]
    return (
        header
        + status_row
        + progress_row
        + [[sg.Frame("运行日志", log_frame, expand_x=True, pad=(10, 10))]]
        + [buttons]
        + footer
    )


def main():
    sg.theme(THEME)
    window = sg.Window(
        "B站收藏夹智能分类",
        _build_layout(),
        finalize=True,
        resizable=True,
    )

    log_q: queue.Queue = queue.Queue()
    runner: PipelineRunner | None = None
    running = False

    def progress(pct: int, msg: str = ""):
        window["-PROG-"].update(current_count=pct)
        window["-STATUS-"].update(f"[{pct}%] {msg}")

    def append_log(msg: str):
        window["-LOG-"].update(msg + "\n", append=True)

    # Initial status
    cfg = load_user_config()
    if cfg.get("USER_MID"):
        append_log(f"已配置用户: MID={cfg['USER_MID']}")
        append_log(f"默认收藏夹 ID: {cfg.get('DEFAULT_FAV_ID', '?')}")
    else:
        append_log("首次使用 — 点击「开始」扫码登录并自动配置")
    append_log("数据文件目录: " + str(_base_dir()))
    append_log("准备就绪")

    if not _check_browsers():
        append_log("⚠ Playwright 浏览器未安装，首次使用前请运行:")
        append_log("  playwright install chromium")

    while True:
        event, _ = window.read(timeout=250)

        # Drain log queue
        while True:
            try:
                mtype, mval = log_q.get_nowait()
            except queue.Empty:
                break
            if mtype == "log":
                append_log(mval)
            elif mtype == "progress":
                progress(*mval)
            elif mtype == "done":
                running = False
                window["-START-"].update(disabled=False)
                window["-STOP-"].update(disabled=True)
                sg.popup_ok(
                    "分类完成！请查看运行日志和 plan.json",
                    title="\U0001f389 完成",
                    keep_on_top=True,
                )
            elif mtype == "error":
                running = False
                window["-START-"].update(disabled=False)
                window["-STOP-"].update(disabled=True)
                progress(0, f"错误: {str(mval)[:60]}")
                sg.popup_error(
                    f"运行出错:\n{mval}", title="错误", keep_on_top=True
                )

        if event in (sg.WIN_CLOSED, "Exit"):
            break

        if event == "-START-" and not running:
            runner = PipelineRunner(log_q, progress)
            threading.Thread(target=runner.run, daemon=True).start()
            running = True
            window["-START-"].update(disabled=True)
            window["-STOP-"].update(disabled=False)
            append_log("━" * 50)
            append_log("\U0001f680 启动分类流程...")

        if event == "-STOP-" and running and runner:
            runner.stop()
            append_log("⏹ 正在停止...")

        if event == "-OPEN-":
            os.startfile(str(_base_dir()))

    window.close()


if __name__ == "__main__":
    _setup_frozen_env()
    main()

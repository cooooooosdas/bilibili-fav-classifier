"""One-click launcher GUI for bilibili-fav-classifier.

Pipeline: collect -> enrich -> classify -> apply
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

import customtkinter as ctk

from bilibili_fav_classifier.apply import apply
from bilibili_fav_classifier.classify_core import autoclassify
from bilibili_fav_classifier.collect import collect
from bilibili_fav_classifier.config import (
    AUTO_CLASSIFY_JSON,
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
        self.log(f"✓ {result.total} 个视频 -> {len(result.groups)} 个文件夹")
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


# ─── Theme ────────────────────────────────────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG = "#1a1b26"
CARD_BG = "#24253a"
ACCENT = "#7aa2f7"
ACCENT_HOVER = "#89b4fa"
SUCCESS = "#9ece6a"
DANGER = "#f7768e"
TEXT = "#c0caf5"
TEXT_DIM = "#565f89"
LOG_BG = "#16161e"


# ─── GUI ──────────────────────────────────────────────────────────

class App(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("B站收藏夹智能分类")
        self.geometry("760x680")
        self.minsize(680, 600)
        self.configure(fg_color=BG)

        self.log_q: queue.Queue = queue.Queue()
        self.runner: PipelineRunner | None = None
        self.running = False

        self._build_ui()
        self._init_status()
        self._poll_queue()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(26, 18))

        ctk.CTkLabel(
            header,
            text="B站收藏夹智能分类",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=24, weight="bold"),
            text_color=TEXT,
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="扫码登录 · 自动拉取 · 智能分类 · 一键整理",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=12),
            text_color=TEXT_DIM,
        ).pack(anchor="w", pady=(2, 0))

        # Status card
        status_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=14)
        status_card.pack(fill="x", padx=28, pady=(0, 14))

        self.status_label = ctk.CTkLabel(
            status_card,
            text="● 就绪",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13, weight="bold"),
            text_color=TEXT_DIM,
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=18, pady=(16, 6))

        self.progress_bar = ctk.CTkProgressBar(
            status_card,
            progress_color=ACCENT,
            fg_color=LOG_BG,
            height=8,
            corner_radius=4,
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=18, pady=(0, 14))

        # Log card
        log_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=14)
        log_card.pack(fill="both", expand=True, padx=28, pady=(0, 14))

        ctk.CTkLabel(
            log_card,
            text="运行日志",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=12, weight="bold"),
            text_color=TEXT_DIM,
            anchor="w",
        ).pack(fill="x", padx=18, pady=(14, 4))

        self.log_box = ctk.CTkTextbox(
            log_card,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=TEXT,
            fg_color=LOG_BG,
            border_width=0,
            corner_radius=8,
            wrap="word",
        )
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.log_box.configure(state="disabled")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=28, pady=(0, 8))

        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="▶  开始一键分类",
            command=self._on_start,
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=14, weight="bold"),
            fg_color=SUCCESS,
            hover_color="#7dc24f",
            text_color="#1a1b26",
            height=46,
            corner_radius=12,
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="⏹  停止",
            command=self._on_stop,
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13),
            fg_color=DANGER,
            hover_color="#e5677e",
            text_color="#1a1b26",
            height=46,
            width=110,
            corner_radius=12,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=(0, 8))

        self.open_btn = ctk.CTkButton(
            btn_frame,
            text="📂  数据文件夹",
            command=self._on_open,
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13),
            fg_color=CARD_BG,
            hover_color=("#2d2e45", "#2d2e45"),
            text_color=TEXT,
            height=46,
            width=140,
            corner_radius=12,
            border_width=1,
            border_color=TEXT_DIM,
        )
        self.open_btn.pack(side="left")

        # Footer
        ctk.CTkLabel(
            self,
            text="🔒 数据仅存储在本地，不会上传到任何服务器",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=10),
            text_color=TEXT_DIM,
        ).pack(pady=(0, 16))

    def _init_status(self):
        cfg = load_user_config()
        if cfg.get("USER_MID"):
            self._append_log(f"已配置用户: MID={cfg['USER_MID']}")
            self._append_log(f"默认收藏夹 ID: {cfg.get('DEFAULT_FAV_ID', '?')}")
        else:
            self._append_log("首次使用 - 点击「开始」扫码登录并自动配置")
        self._append_log("数据文件目录: " + str(_base_dir()))
        self._append_log("准备就绪")

        if not _check_browsers():
            self._append_log("⚠ Playwright 浏览器未安装，首次使用前请运行:")
            self._append_log("  playwright install chromium")

    def _set_status(self, text: str, color: str = TEXT):
        self.status_label.configure(text=text, text_color=color)

    def _set_progress(self, pct: int):
        self.progress_bar.set(pct / 100)

    def _append_log(self, msg: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _poll_queue(self):
        while True:
            try:
                mtype, mval = self.log_q.get_nowait()
            except queue.Empty:
                break
            if mtype == "log":
                self._append_log(mval)
            elif mtype == "progress":
                pct, msg = mval
                self._set_progress(pct)
                self._set_status(f"● {msg}", ACCENT)
            elif mtype == "done":
                self._finish(success=True)
            elif mtype == "error":
                self._set_status(f"● 错误: {str(mval)[:50]}", DANGER)
                self._finish(success=False)
        self.after(200, self._poll_queue)

    def _finish(self, success: bool):
        self.running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        if success:
            self._set_status("● 全部完成", SUCCESS)
            self._show_toast("分类完成！请查看运行日志和 plan.json")
        else:
            self._set_status("● 运行出错", DANGER)

    def _show_toast(self, msg: str):
        toast = ctk.CTkToplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(fg_color=CARD_BG)

        ctk.CTkLabel(
            toast,
            text=msg,
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13),
            text_color=TEXT,
            padx=24,
            pady=14,
        ).pack()

        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - toast.winfo_width()) // 2
        y = self.winfo_y() + 80
        toast.geometry(f"+{x}+{y}")
        toast.after(2500, toast.destroy)

    def _on_start(self):
        if self.running:
            return
        self.runner = PipelineRunner(self.log_q, self._progress_cb)
        threading.Thread(target=self.runner.run, daemon=True).start()
        self.running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._append_log("━" * 50)
        self._append_log("\U0001f680 启动分类流程...")

    def _progress_cb(self, pct: int, msg: str):
        self.log_q.put(("progress", (pct, msg)))

    def _on_stop(self):
        if self.runner and self.running:
            self.runner.stop()
            self._append_log("⏹ 正在停止...")

    def _on_open(self):
        os.startfile(str(_base_dir()))


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    _setup_frozen_env()
    main()

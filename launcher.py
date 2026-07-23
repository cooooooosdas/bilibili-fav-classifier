"""One-click launcher GUI for bilibili-fav-classifier.

Pipeline: collect -> enrich -> classify -> apply
Works as a Python script or a PyInstaller-frozen .exe.
"""
from __future__ import annotations

import asyncio
import json
import math
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
        self.progress(5, "启动浏览器...", 0)

        bundled = _find_bundled_browser()

        try:
            asyncio.run(collect(bundled))
        except Exception as exc:
            self.log(f"❌ 拉取失败: {exc}")
            return

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
        self.progress(25, "收藏夹拉取完成", 0)

    def _enrich(self):
        self.log("━" * 50)
        self.log("步骤 2/4: 补充视频标签和分区")
        self.progress(30, "分析视频元数据...", 1)
        session = Session.load()
        enrich_meta(session=session)
        self.progress(50, "标签补充完成", 1)
        self.log("✓ 标签/分区补充完成")

    def _classify(self):
        self.log("━" * 50)
        self.log("步骤 3/4: 智能分类")
        self.progress(55, "分析分类...", 2)

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

        self.progress(75, "分类完成", 2)
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
        self.progress(80, "执行分类...", 3)
        session = Session.load()
        apply(session.http(), session.csrf)
        self.progress(100, "全部完成!", 3)
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
CARD_BG_HOVER = "#2a2b42"
ACCENT = "#7aa2f7"
ACCENT_SOFT = "#3b4261"
SUCCESS = "#9ece6a"
DANGER = "#f7768e"
WARNING = "#e0af68"
TEXT = "#c0caf5"
TEXT_DIM = "#565f89"
TEXT_MID = "#9aa5ce"
LOG_BG = "#14141c"
DIVIDER = "#2a2b42"

FONT_UI = "Microsoft YaHei UI"
FONT_MONO = "Cascadia Mono"

STEPS = ["拉取", "补充", "分类", "应用"]


# ─── Color utilities ──────────────────────────────────────────────

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _lerp_color(c1: str, c2: str, t: float) -> str:
    """Interpolate between two hex colors. t in [0, 1]."""
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return _rgb_to_hex((
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    ))


# ─── GUI ──────────────────────────────────────────────────────────

class App(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("B站收藏夹智能分类")
        self.geometry("780x720")
        self.minsize(700, 640)
        self.configure(fg_color=BG)
        self.log_q: queue.Queue = queue.Queue()
        self.runner: PipelineRunner | None = None
        self.running = False

        self._target_progress = 0.0
        self._current_progress = 0.0
        self._pulse_phase = 0.0
        self._current_step = -1
        self._toast = None

        self._build_ui()
        self._init_status()
        self._poll_queue()
        self._tick_animation()
        self.attributes("-alpha", 0.0)
        self._fade_in(0.0)

    def _build_ui(self):
        # ── Header ─────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=32, pady=(28, 20))

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(fill="x")

        ctk.CTkLabel(
            title_row,
            text="favorites",
            font=ctk.CTkFont(family=FONT_UI, size=22, weight="bold"),
            text_color=ACCENT,
        ).pack(side="left")
        ctk.CTkLabel(
            title_row,
            text="  收藏夹智能分类",
            font=ctk.CTkFont(family=FONT_UI, size=22, weight="bold"),
            text_color=TEXT,
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text="扫码登录  ·  自动拉取  ·  智能分类  ·  一键整理",
            font=ctk.CTkFont(family=FONT_UI, size=11),
            text_color=TEXT_DIM,
        ).pack(anchor="w", pady=(4, 0))

        # ── Step indicator card ────────────────────────────────
        step_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=16)
        step_card.pack(fill="x", padx=32, pady=(0, 12))

        step_row = ctk.CTkFrame(step_card, fg_color="transparent")
        step_row.pack(fill="x", padx=20, pady=(18, 6))

        self.step_circles = []
        self.step_labels = []
        self.step_lines = []
        for i, name in enumerate(STEPS):
            circle = ctk.CTkLabel(
                step_row,
                text="○",
                width=34,
                height=34,
                corner_radius=17,
                fg_color=ACCENT_SOFT,
                text_color=TEXT_DIM,
                font=ctk.CTkFont(family=FONT_UI, size=16, weight="bold"),
            )
            circle.pack(side="left")
            self.step_circles.append(circle)

            ctk.CTkLabel(
                step_row,
                text=name,
                font=ctk.CTkFont(family=FONT_UI, size=11),
                text_color=TEXT_DIM,
            ).pack(side="left", padx=(6, 0))
            self.step_labels.append(None)

            if i < len(STEPS) - 1:
                line = ctk.CTkFrame(
                    step_row, fg_color=ACCENT_SOFT, height=2, width=44,
                )
                line.pack(side="left", fill="x", expand=True, padx=10, pady=0)
                self.step_lines.append(line)

        # ── Status card ────────────────────────────────────────
        status_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=16)
        status_card.pack(fill="x", padx=32, pady=(0, 12))

        self.status_label = ctk.CTkLabel(
            status_card,
            text="●  就绪",
            font=ctk.CTkFont(family=FONT_UI, size=13, weight="bold"),
            text_color=TEXT_MID,
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=20, pady=(16, 8))

        self.progress_bar = ctk.CTkProgressBar(
            status_card,
            progress_color=ACCENT,
            fg_color=ACCENT_SOFT,
            height=6,
            corner_radius=3,
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 16))

        # ── Log card ───────────────────────────────────────────
        log_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=16)
        log_card.pack(fill="both", expand=True, padx=32, pady=(0, 12))

        log_header = ctk.CTkFrame(log_card, fg_color="transparent")
        log_header.pack(fill="x", padx=20, pady=(14, 2))

        ctk.CTkLabel(
            log_header,
            text="运行日志",
            font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold"),
            text_color=TEXT_DIM,
            anchor="w",
        ).pack(side="left")

        self.log_box = ctk.CTkTextbox(
            log_card,
            font=ctk.CTkFont(family=FONT_MONO, size=12),
            text_color=TEXT,
            fg_color=LOG_BG,
            border_width=0,
            corner_radius=10,
            wrap="word",
        )
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(4, 14))
        self._setup_log_tags()
        self.log_box.configure(state="disabled")

        # ── Buttons ────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=32, pady=(0, 6))

        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="▶  开始一键分类",
            command=self._on_start,
            font=ctk.CTkFont(family=FONT_UI, size=14, weight="bold"),
            fg_color=SUCCESS,
            hover_color="#7dc24f",
            text_color="#14141c",
            height=48,
            corner_radius=12,
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="⏹  停止",
            command=self._on_stop,
            font=ctk.CTkFont(family=FONT_UI, size=13, weight="bold"),
            fg_color=DANGER,
            hover_color="#e5677e",
            text_color="#14141c",
            height=48,
            width=100,
            corner_radius=12,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=(0, 8))

        self.open_btn = ctk.CTkButton(
            btn_frame,
            text="📂  文件夹",
            command=self._on_open,
            font=ctk.CTkFont(family=FONT_UI, size=13),
            fg_color="transparent",
            hover_color=CARD_BG_HOVER,
            text_color=TEXT_MID,
            height=48,
            width=110,
            corner_radius=12,
            border_width=1,
            border_color=DIVIDER,
        )
        self.open_btn.pack(side="left")

        # ── Footer ─────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="🔒  数据仅存储在本地  ·  不会上传到任何服务器",
            font=ctk.CTkFont(family=FONT_UI, size=10),
            text_color=TEXT_DIM,
        ).pack(pady=(0, 18))

    def _setup_log_tags(self):
        """Configure color tags for different log message types."""
        self.log_box.tag_config("success", foreground=SUCCESS)
        self.log_box.tag_config("error", foreground=DANGER)
        self.log_box.tag_config("warning", foreground=WARNING)
        self.log_box.tag_config("step", foreground=ACCENT)
        self.log_box.tag_config("dim", foreground=TEXT_DIM)
        self.log_box.tag_config("info", foreground=TEXT_MID)

    def _init_status(self):
        cfg = load_user_config()
        if cfg.get("USER_MID"):
            self._append_log(f"已配置用户: MID={cfg['USER_MID']}", "info")
            self._append_log(f"默认收藏夹 ID: {cfg.get('DEFAULT_FAV_ID', '?')}", "info")
        else:
            self._append_log("首次使用 - 点击「开始」扫码登录并自动配置", "info")
        self._append_log("数据文件目录: " + str(_base_dir()), "dim")
        self._append_log("准备就绪", "success")

        if not _check_browsers():
            self._append_log("⚠ Playwright 浏览器未安装，首次使用前请运行:", "warning")
            self._append_log("  playwright install chromium", "dim")

    # ── Log output ──────────────────────────────────────────

    def _append_log(self, msg: str, tag: str = ""):
        self.log_box.configure(state="normal")
        if tag:
            self.log_box.insert("end", msg + "\n", tag)
        else:
            self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _append_log_smart(self, msg: str):
        """Auto-detect log type from prefix and apply color tag."""
        tag = ""
        if msg.startswith("✓"):
            tag = "success"
        elif msg.startswith("❌"):
            tag = "error"
        elif msg.startswith("⚠"):
            tag = "warning"
        elif msg.startswith("━"):
            tag = "dim"
        elif msg.startswith("步骤"):
            tag = "step"
        elif msg.startswith("    "):
            tag = "info"
        self._append_log(msg, tag)

    # ── Animation loop ──────────────────────────────────────

    def _tick_animation(self):
        """Single animation tick: smooth progress + status pulse."""
        # Smooth progress interpolation
        if abs(self._current_progress - self._target_progress) > 0.002:
            self._current_progress += (
                self._target_progress - self._current_progress
            ) * 0.12
            self.progress_bar.set(self._current_progress)
        elif self._current_progress != self._target_progress:
            self._current_progress = self._target_progress
            self.progress_bar.set(self._current_progress)

        # Pulse status dot while running
        if self.running:
            self._pulse_phase += 0.06
            t = 0.5 + 0.5 * math.sin(self._pulse_phase)
            color = _lerp_color(ACCENT, SUCCESS, t * 0.4)
            text = self.status_label.cget("text")
            if text.startswith("●"):
                self.status_label.configure(text_color=color)

        self.after(16, self._tick_animation)

    def _fade_in(self, alpha: float):
        if alpha < 1.0:
            self.attributes("-alpha", alpha)
            self.after(12, lambda: self._fade_in(min(alpha + 0.06, 1.0)))
        else:
            self.attributes("-alpha", 1.0)

    # ── Step indicator ──────────────────────────────────────

    def _set_step(self, step_idx: int):
        """Update the 4-step indicator. step_idx: 0-3 active, -1 none."""
        self._current_step = step_idx
        for i, circle in enumerate(self.step_circles):
            if i < step_idx:
                circle.configure(text="✓", fg_color=SUCCESS, text_color="#14141c")
            elif i == step_idx:
                circle.configure(text="●", fg_color=ACCENT, text_color="#14141c")
            else:
                circle.configure(text="○", fg_color=ACCENT_SOFT, text_color=TEXT_DIM)
        for i, line in enumerate(self.step_lines):
            if i < step_idx:
                line.configure(fg_color=SUCCESS)
            else:
                line.configure(fg_color=ACCENT_SOFT)

    # ── Status & progress ───────────────────────────────────

    def _set_status(self, text: str, color: str = TEXT):
        self.status_label.configure(text=text, text_color=color)

    def _set_progress(self, pct: int):
        self._target_progress = pct / 100

    # ── Queue polling ───────────────────────────────────────

    def _poll_queue(self):
        while True:
            try:
                mtype, mval = self.log_q.get_nowait()
            except queue.Empty:
                break
            if mtype == "log":
                self._append_log_smart(mval)
            elif mtype == "progress":
                pct, msg, step = mval
                self._set_progress(pct)
                self._set_status(f"●  {msg}", ACCENT)
                self._set_step(step)
            elif mtype == "done":
                self._finish(success=True)
            elif mtype == "error":
                self._set_status(f"●  错误: {str(mval)[:50]}", DANGER)
                self._finish(success=False)
        self.after(120, self._poll_queue)

    def _finish(self, success: bool):
        self.running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        if success:
            self._set_status("●  全部完成", SUCCESS)
            self._set_step(4)
            self._show_toast("🎉  分类完成！")
        else:
            self._set_status("●  运行出错", DANGER)

    # ── Toast ───────────────────────────────────────────────

    def _show_toast(self, msg: str):
        if self._toast is not None:
            self._toast.destroy()
        toast = ctk.CTkToplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(fg_color=SUCCESS)
        toast.attributes("-alpha", 0.0)
        self._toast = toast

        ctk.CTkLabel(
            toast,
            text=msg,
            font=ctk.CTkFont(family=FONT_UI, size=14, weight="bold"),
            text_color="#14141c",
            padx=32,
            pady=16,
        ).pack()

        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - toast.winfo_width()) // 2
        y = self.winfo_y() + 90
        toast.geometry(f"+{x}+{y}")
        self._fade_toast(toast, 0.0, fade_in=True)

    def _fade_toast(self, toast, alpha, fade_in):
        if fade_in:
            if alpha < 1.0:
                toast.attributes("-alpha", min(alpha + 0.1, 1.0))
                self.after(16, lambda: self._fade_toast(toast, alpha + 0.1, True))
            else:
                self.after(1800, lambda: self._fade_toast(toast, 1.0, False))
        else:
            if alpha > 0:
                toast.attributes("-alpha", max(alpha - 0.08, 0.0))
                self.after(16, lambda: self._fade_toast(toast, alpha - 0.08, False))
            else:
                toast.destroy()
                if self._toast is toast:
                    self._toast = None

    # ── Button handlers ─────────────────────────────────────

    def _on_start(self):
        if self.running:
            return
        self.runner = PipelineRunner(self.log_q, self._progress_cb)
        threading.Thread(target=self.runner.run, daemon=True).start()
        self.running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._append_log("━" * 50, "dim")
        self._append_log("🚀 启动分类流程...", "step")

    def _progress_cb(self, pct: int, msg: str, step: int = -1):
        self.log_q.put(("progress", (pct, msg, step)))

    def _on_stop(self):
        if self.runner and self.running:
            self.runner.stop()
            self._append_log("⏹ 正在停止...", "warning")

    def _on_open(self):
        os.startfile(str(_base_dir()))


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    _setup_frozen_env()
    main()

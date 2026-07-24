"""Build script: package bilibili-fav-classifier as a standalone .exe.

Usage:
    python build.py

Output:
    dist/B站收藏夹分类/B站收藏夹分类.exe   (+ data files + browsers)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "B站收藏夹分类"
PROJECT_ROOT = Path(__file__).parent


def _run(cmd: list[str], **kwargs):
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, **kwargs)


def _dir_size_mb(path: Path) -> float:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / 1024 / 1024


def _install_browsers():
    """Install Playwright Chromium browser."""
    print("\n[1/5] Installing Playwright browsers...")
    _run([sys.executable, "-m", "playwright", "install", "chromium"])


def _build_exe():
    """Run PyInstaller to build the .exe."""
    print("\n[2/5] Building with PyInstaller...")

    spec_file = PROJECT_ROOT / "build.spec"
    _run([sys.executable, "-m", "PyInstaller", str(spec_file), "-y"])

    dist_dir = PROJECT_ROOT / "dist" / APP_NAME
    if not dist_dir.exists():
        raise RuntimeError(f"Build failed — {dist_dir} not found")
    print(f"    Output: {dist_dir}")


def _copy_browsers(dist_dir: Path):
    """Copy Playwright browser binaries to dist folder."""
    print("\n[3/5] Copying Playwright browsers...")
    browsers_src = Path.home() / "AppData" / "Local" / "ms-playwright"
    browsers_dst = dist_dir / "ms-playwright"

    if not browsers_src.exists():
        print("    Browsers not found at default location, skipping")
        return

    if browsers_dst.exists():
        shutil.rmtree(browsers_dst)
    shutil.copytree(browsers_src, browsers_dst)
    print(f"    Copied {_dir_size_mb(browsers_dst):.0f} MB to {browsers_dst}")


def _copy_templates(dist_dir: Path):
    """Copy config/seed templates to dist folder."""
    print("\n[4/5] Copying template files...")
    templates = [
        "bilibili_fav_classifier/config_template.json",
        "bilibili_fav_classifier/seed_mappings_template.json",
    ]
    for tpl in templates:
        src = PROJECT_ROOT / tpl
        if src.exists():
            shutil.copy2(src, dist_dir / src.name)
            print(f"    {src.name}")


def _write_readme(dist_dir: Path):
    """Write a usage guide for the dist folder."""
    print("\n[5/5] Writing usage guide...")
    readme = dist_dir / "使用说明.txt"

    sep = "=" * 42
    content = (
        "[*] B站收藏夹智能分类 - 使用说明\n"
        f"{sep}\n"
        "\n"
        "  1. 双击运行 B站收藏夹分类.exe\n"
        "  2. 在弹出的浏览器中扫码登录 B站\n"
        "  3. 程序自动完成: 拉取 -> 补充标签 -> 智能分类 -> 移动视频\n"
        "\n"
        "[i] 数据文件说明:\n"
        "  config.json          -- 用户配置 (MID, 默认收藏夹ID)\n"
        "  cookies.json         -- 登录凭证\n"
        "  favs.json            -- 收藏夹视频数据\n"
        "  seed_mappings.json   -- UP主所属映射表 (可编辑)\n"
        "  plan.json            -- 分类计划 (应用前可手动修改)\n"
        "  enrich_cache.json    -- 标签/分区缓存\n"
        "  apply_log.json       -- 执行日志\n"
        "\n"
        "注意事项:\n"
        "  - 数据仅存储在本地，不会上传到任何服务器\n"
        "  - 分类结果不理想时，可编辑 seed_mappings.json 后重新运行\n"
        "  - 若要重新登录，删除 cookies.json 后重新运行\n"
        "  - 若分类结果中 '其他'过多，可在 seed_mappings.json 中添加UP主映射\n"
        "\n"
        "[!] 问题排查:\n"
        "  - 浏览器无法启动: 确保系统安装了 Chrome 或 Edge\n"
        "  - 分类结果不理想: 查看 seed_mappings.json 是否正确\n"
        "  - 没有标签: 运行 enrich_meta 步骤补充\n"
    )

    readme.write_text(content, encoding="utf-8")
    print(f"    {readme.name}")


def main():
    os.chdir(PROJECT_ROOT)

    _install_browsers()
    _build_exe()

    dist_dir = PROJECT_ROOT / "dist" / APP_NAME
    _copy_browsers(dist_dir)
    _copy_templates(dist_dir)
    _write_readme(dist_dir)

    size = _dir_size_mb(dist_dir)
    print(f"\n{'=' * 50}")
    print(f"Build complete!")
    print(f"   Executable: {dist_dir / APP_NAME}.exe")
    print(f"   Total size: {size:.0f} MB")
    print(f"   Location:   {dist_dir}")
    print()
    print("  You can now distribute the entire 'dist/B站收藏夹分类' folder.")


if __name__ == "__main__":
    main()

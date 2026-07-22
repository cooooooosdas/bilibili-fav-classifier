"""Generate logos for bilibili-fav-classifier."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "assets"
OUT.mkdir(exist_ok=True)

# ── Palette ────────────────────────────────────────────────────

BG = "#1a1b26"
ACCENT = "#7aa2f7"
BILI_PINK = "#FB7299"
SUCCESS = "#9ece6a"
WHITE = "#c0caf5"


# ── Helpers ────────────────────────────────────────────────────

def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def circle(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill: str):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


def rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[tuple[int, int], tuple[int, int]],
    r: int,
    fill: str,
):
    x0, y0 = xy[0]
    x1, y1 = xy[1]
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    draw.ellipse([x0, y0, x0 + 2 * r, y0 + 2 * r], fill=fill)
    draw.ellipse([x1 - 2 * r, y0, x1, y0 + 2 * r], fill=fill)
    draw.ellipse([x0, y1 - 2 * r, x0 + 2 * r, y1], fill=fill)
    draw.ellipse([x1 - 2 * r, y1 - 2 * r, x1, y1], fill=fill)


# ── Main logo (256x256) ────────────────────────────────────────

def draw_main_logo(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), hex_to_rgb(BG))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2

    # Outer glow ring
    for i in range(4, 0, -1):
        alpha = int(30 - i * 6)
        r = cx - 12 - i * 4
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=(*hex_to_rgb(ACCENT), alpha),
            width=2,
        )

    # Main circle background
    main_r = cx - 16
    draw.ellipse([cx - main_r, cy - main_r, cx + main_r, cy + main_r], fill=BG)

    # Accent ring
    ring_r = cx - 16
    draw.ellipse(
        [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
        outline=ACCENT,
        width=4,
    )

    # Inner gradient-ish circle
    inner_r = cx - 26
    draw.ellipse(
        [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
        fill=(*hex_to_rgb(ACCENT), 25),
    )

    # ── Folder icon ──────────────────────────────────────────
    folder_y = cy - 18
    folder_h = 64
    folder_w = 110
    tab_w = 50
    tab_h = 20

    # Folder tab
    rounded_rect(
        draw,
        ((cx - folder_w // 2, folder_y - tab_h + 8), (cx + folder_w // 2, folder_y + 8)),
        8,
        fill=WHITE,
    )

    # Folder body
    rounded_rect(
        draw,
        ((cx - folder_w // 2, folder_y), (cx + folder_w // 2, folder_y + folder_h)),
        10,
        fill=WHITE,
    )

    # Folder inner (lighter shade for depth)
    inner_folder = Image.new("RGBA", img.size, (0, 0, 0, 0))
    inner_draw = ImageDraw.Draw(inner_folder)
    rounded_rect(
        inner_draw,
        (
            (cx - folder_w // 2 + 8, folder_y + 8),
            (cx + folder_w // 2 - 8, folder_y + folder_h - 4),
        ),
        6,
        fill=(*hex_to_rgb(BG), 100),
    )
    img = Image.alpha_composite(img, inner_folder)
    draw = ImageDraw.Draw(img)

    # ── Star / sparkle (classification spark) ───────────────
    star_x = cx + 28
    star_y = folder_y + folder_h - 24
    star_r = 16

    # Star shape
    points = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        r = star_r if i % 2 == 0 else star_r // 2
        points.append((star_x + r * math.cos(angle), star_y + r * math.sin(angle)))

    draw.polygon(points, fill=BILI_PINK)

    # Sparkle lines
    for angle_deg in [45, 135, 225, 315]:
        angle = math.radians(angle_deg)
        x1 = star_x + (star_r + 6) * math.cos(angle)
        y1 = star_y + (star_r + 6) * math.sin(angle)
        x2 = star_x + (star_r + 14) * math.cos(angle)
        y2 = star_y + (star_r + 14) * math.sin(angle)
        draw.line([(x1, y1), (x2, y2)], fill=BILI_PINK, width=2)

    # ── Small checkmarks on folders ─────────────────────────
    check_x = cx - 24
    check_y = folder_y + 22
    draw.line(
        [(check_x, check_y), (check_x + 10, check_y + 12), (check_x + 24, check_y - 8)],
        fill=SUCCESS,
        width=5,
    )

    # ── Text: "Fav" at bottom ────────────────────────────────
    try:
        font = ImageFont.truetype("msyh.ttc", 28)  # Microsoft YaHei
    except Exception:
        try:
            font = ImageFont.truetype("simhei.ttf", 28)
        except Exception:
            font = ImageFont.load_default()

    text = "Fav"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    text_y = folder_y + folder_h - th - 8
    draw.text((cx - tw // 2, text_y), text, fill=ACCENT, font=font)

    return img


# ── Rounded square icon (512x512) ─────────────────────────────

def draw_square_logo(size: int = 512) -> Image.Image:
    main = draw_main_logo(256)
    img = Image.new("RGBA", (size, size), hex_to_rgb(BG))
    # Place main logo centered
    img.paste(main, ((size - 256) // 2, (size - 256) // 2), main)

    # Scale up for larger size
    img = img.resize((size, size), Image.LANCZOS)

    # Rounded corners
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    r = size // 8
    mask_draw.rounded_rectangle([(0, 0), (size, size)], radius=r, fill=255)
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(img, (0, 0), mask)
    return output


# ── Favicon (64x64) ───────────────────────────────────────────

def draw_favicon(size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = size // 2 - 2

    # Circle
    draw.ellipse([2, 2, size - 2, size - 2], fill=BG)
    draw.ellipse([2, 2, size - 2, size - 2], outline=ACCENT, width=3)

    # Simplified folder
    fy = cy - 6
    fw = 36
    fh = 22
    draw.rounded_rectangle(
        [cx - fw // 2, fy - 4, cx + fw // 2, fy + fh - 4],
        radius=4,
        fill=WHITE,
    )
    draw.rounded_rectangle(
        [cx - fw // 2, fy, cx + fw // 2, fy + fh],
        radius=4,
        fill=WHITE,
    )

    # Check
    draw.line(
        [(cx - 8, fy + 8), (cx - 2, fy + 14), (cx + 8, fy + 4)],
        fill=SUCCESS,
        width=3,
    )

    # Star
    sx, sy = cx + 10, fy + fh - 8
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        sr = 7 if i % 2 == 0 else 3
        pts.append((sx + sr * math.cos(a), sy + sr * math.sin(a)))
    draw.polygon(pts, fill=BILI_PINK)

    return img


# ── Banner (1200x630) ──────────────────────────────────────────

def draw_banner(w: int = 1200, h: int = 630) -> Image.Image:
    img = Image.new("RGBA", (w, h), hex_to_rgb(BG))
    draw = ImageDraw.Draw(img)

    # Subtle grid pattern
    for x in range(0, w, 40):
        draw.line([(x, 0), (x, h)], fill=(*hex_to_rgb(ACCENT), 8), width=1)
    for y in range(0, h, 40):
        draw.line([(0, y), (w, y)], fill=(*hex_to_rgb(ACCENT), 8), width=1)

    # Gradient accent bar at top
    for y in range(0, 6):
        t = y / 6
        c = _lerp_hex(ACCENT, BILI_PINK, t)
        draw.line([(0, y), (w, y)], fill=c)

    # Logo
    logo = draw_main_logo(256)
    img.paste(logo, (80, (h - 256) // 2), logo)

    # Title text
    try:
        font_big = ImageFont.truetype("msyh.ttc", 56)
        font_sm = ImageFont.truetype("msyh.ttc", 30)
    except Exception:
        try:
            font_big = ImageFont.truetype("simhei.ttf", 56)
            font_sm = ImageFont.truetype("simhei.ttf", 28)
        except Exception:
            font_big = ImageFont.load_default()
            font_sm = ImageFont.load_default()

    title_y = h // 2 - 50
    draw.text((380, title_y), "B站收藏夹", fill=WHITE, font=font_big)
    draw.text((380, title_y + 68), "智能分类", fill=ACCENT, font=font_big)

    # Subtitle
    draw.text(
        (380, title_y + 160),
        "扫码登录 · 自动拉取 · 智能分类 · 一键整理",
        fill=WHITE,
        font=font_sm,
    )

    # Features
    features = ["四层智能匹配", "零配置开箱即用", "数据本地存储"]
    for i, feat in enumerate(features):
        draw.text((380, title_y + 220 + i * 38), f"·  {feat}", fill=WHITE, font=font_sm)

    # Corner decoration
    corner_x, corner_y = w - 80, 80
    for i in range(3):
        draw.ellipse(
            [
                corner_x - i * 20,
                corner_y - i * 20,
                corner_x + 20 - i * 20,
                corner_y + 20 - i * 20,
            ],
            outline=(*hex_to_rgb(ACCENT), 40 + i * 20),
            width=2,
        )

    return img


def _lerp_hex(c1: str, c2: str, t: float) -> str:
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"


TEXT_DIM = "#565f89"

# ── Generate ───────────────────────────────────────────────────

print("Generating logos...")

main = draw_main_logo(256)
main.save(OUT / "logo_256.png")
print(f"  logo_256.png  ({main.size})")

square = draw_square_logo(512)
square.save(OUT / "logo_512.png")
print(f"  logo_512.png  ({square.size})")

favicon = draw_favicon(64)
favicon.save(OUT / "favicon_64.png")
print(f"  favicon_64.png  ({favicon.size})")

banner = draw_banner()
banner.save(OUT / "banner_1200x630.png")
print(f"  banner_1200x630.png  ({banner.size})")

# ICO for window icon (multi-size)
ico = Image.new("RGBA", (256, 256), hex_to_rgb(BG))
ico.paste(main, (0, 0), main)
ico.save(OUT / "app_icon.ico", format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print(f"  app_icon.ico")

print(f"\nAll logos saved to {OUT}")
print("Done!")

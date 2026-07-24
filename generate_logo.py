"""Replace generated logos with custom user icon."""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SRC = Path(__file__).parent / "src_logo.png"
OUT = Path(__file__).parent / "assets"
OUT.mkdir(exist_ok=True)

# Load source
img = Image.open(SRC).convert("RGBA")
print(f"Source: {img.size}")

# Generate square PNG at various sizes
for size in [256, 512]:
    resized = img.resize((size, size), Image.LANCZOS)
    out_path = OUT / f"logo_{size}.png"
    resized.save(out_path)
    print(f"  logo_{size}.png ({resized.size})")

# Favicon
favicon = img.resize((64, 64), Image.LANCZOS)
favicon.save(OUT / "favicon_64.png")
print(f"  favicon_64.png ({favicon.size})")

# ICO with multiple sizes
ico = img.resize((256, 256), Image.LANCZOS)
ico.save(OUT / "app_icon.ico", format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print(f"  app_icon.ico")

# Banner (paste icon on left, text on right)
banner = Image.new("RGBA", (1200, 630), (26, 27, 38, 255))
draw = ImageDraw.Draw(banner)

# Icon on left
icon_size = 280
icon_resized = img.resize((icon_size, icon_size), Image.LANCZOS)
banner.paste(icon_resized, (90, (630 - icon_size) // 2), icon_resized)

# Gradient accent line at top
for y in range(0, 6):
    t = y / 6
    r = int(122 + (251 - 122) * t)
    g = int(162 + (114 - 162) * t)
    b = int(247 + (153 - 247) * t)
    draw.line([(0, y), (1200, y)], fill=(r, g, b))

# Title text
try:
    font_big = ImageFont.truetype("msyh.ttc", 56)
    font_sm = ImageFont.truetype("msyh.ttc", 26)
except Exception:
    try:
        font_big = ImageFont.truetype("simhei.ttf", 56)
        font_sm = ImageFont.truetype("simhei.ttf", 26)
    except Exception:
        font_big = font_sm = ImageFont.load_default()

title_y = 630 // 2 - 80
draw.text((420, title_y), "B站收藏夹", fill=(192, 202, 245, 255), font=font_big)
draw.text((420, title_y + 72), "智能分类", fill=(122, 162, 247, 255), font=font_big)

# Subtitle
draw.text((420, title_y + 160), "扫码登录 · 自动拉取 · 智能分类 · 一键整理", fill=(192, 202, 245, 200), font=font_sm)

# Features
features = ["四层智能匹配", "零配置开箱即用", "数据本地存储"]
for i, feat in enumerate(features):
    draw.text((420, title_y + 210 + i * 38), f"·  {feat}", fill=(192, 202, 245, 180), font=font_sm)

banner.save(OUT / "banner_1200x630.png")
print(f"  banner_1200x630.png ({banner.size})")

print("\nAll done!")

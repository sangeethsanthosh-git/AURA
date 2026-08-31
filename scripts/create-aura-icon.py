from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "public" / "assets"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def gradient(size: int = 1024) -> Image.Image:
    img = Image.new("RGBA", (size, size), "white")
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (size * 2)
            r = int(235 - 85 * t)
            g = int(238 - 120 * t)
            b = int(255 - 20 * t)
            px[x, y] = (r, g, b, 255)
    return img


def create_icon() -> Image.Image:
    canvas = Image.new("RGBA", (1024, 1024), (255, 255, 255, 0))
    base = Image.new("RGBA", (820, 820), (244, 243, 255, 255))

    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((8, 8, 812, 812), radius=180, fill=(63, 78, 255, 48))
    shadow = shadow.filter(ImageFilter.GaussianBlur(40))
    canvas.alpha_composite(shadow, (100, 100))

    panel = Image.new("RGBA", base.size, (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel)
    panel_draw.rounded_rectangle((0, 0, 820, 820), radius=180, fill=(247, 246, 255, 255))
    panel = panel.filter(ImageFilter.GaussianBlur(1))
    canvas.alpha_composite(panel, (102, 102))

    blob = gradient(560).resize((560, 560))
    mask = Image.new("L", (560, 560), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((32, 16, 528, 528), radius=220, fill=255)
    mask_draw.ellipse((16, 400, 170, 540), fill=255)
    mask_draw.ellipse((175, 460, 275, 560), fill=255)
    mask_draw.ellipse((350, 456, 460, 560), fill=255)
    blob.putalpha(mask)
    blob = blob.filter(ImageFilter.GaussianBlur(2))
    canvas.alpha_composite(blob, (232, 220))

    draw = ImageDraw.Draw(canvas)

    # Face mark
    white = (252, 252, 255, 255)
    draw.rounded_rectangle((486, 400, 558, 562), radius=32, fill=white)
    draw.rounded_rectangle((606, 382, 678, 548), radius=32, fill=white)
    draw.rounded_rectangle((392, 498, 458, 564), radius=26, fill=white)
    draw.rounded_rectangle((388, 520, 576, 590), radius=34, fill=white)

    # Text
    try:
        font = ImageFont.truetype("arial.ttf", 110)
    except Exception:
        font = ImageFont.load_default()
    try:
        font_small = ImageFont.truetype("arial.ttf", 44)
    except Exception:
        font_small = ImageFont.load_default()

    text = "AURA"
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (1024 - (bbox[2] - bbox[0])) // 2
    y = 820
    draw.text((x, y), text, font=font, fill=(88, 64, 248, 255))

    return canvas


def main() -> None:
    icon = create_icon()
    png_path = OUT_DIR / "aura-app-icon.png"
    ico_path = OUT_DIR / "aura-app-icon.ico"
    icon.save(png_path)
    icon.save(ico_path, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Wrote {png_path}")
    print(f"Wrote {ico_path}")


if __name__ == "__main__":
    main()

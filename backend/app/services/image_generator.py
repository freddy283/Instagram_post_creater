import os
import textwrap
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import uuid

IMAGES_DIR = "./images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# Dimensions
WIDTH = 1080
HEIGHT = 1080

BACKGROUNDS = {
    "black": (0, 0, 0),
    "dark_grey": (28, 28, 28),
}
GOLD = (212, 175, 55)
GOLD_LIGHT = (235, 205, 90)
WHITE = (245, 245, 245)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a font, falling back to default if TTF not available."""
    # Try system fonts
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_quote_image(
    quote: str,
    author: str = "",
    background: str = "dark_grey",
    user_id: str = "",
    preview: bool = False,
    watermark: str = "DailyQuote",
) -> str:
    """Generate a 1080x1080 quote image and return its file path."""
    bg_color = BACKGROUNDS.get(background, BACKGROUNDS["dark_grey"])

    img = Image.new("RGB", (WIDTH, HEIGHT), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Subtle noise/gradient overlay for depth
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for i in range(HEIGHT):
        alpha = int(20 * (i / HEIGHT))
        ov_draw.line([(0, i), (WIDTH, i)], fill=(255, 255, 200, alpha))
    img.paste(Image.alpha_composite(overlay.convert("RGBA"), overlay).convert("RGB"),
              mask=None if True else overlay)

    # Gold decorative line top
    margin = 80
    draw.line([(margin, 120), (WIDTH - margin, 120)], fill=GOLD, width=1)
    draw.line([(margin, 960), (WIDTH - margin, 960)], fill=GOLD, width=1)

    # Small diamond ornament
    cx = WIDTH // 2
    draw.polygon([(cx, 110), (cx + 8, 120), (cx, 130), (cx - 8, 120)], fill=GOLD)
    draw.polygon([(cx, 950), (cx + 8, 960), (cx, 970), (cx - 8, 960)], fill=GOLD)

    # Quote font — start large and shrink to fit
    padding = 120
    max_text_width = WIDTH - padding * 2
    font_size = 72
    min_font = 32

    while font_size >= min_font:
        font = _load_font(font_size)
        lines = _wrap_text(f"\u201c{quote}\u201d", font, max_text_width, draw)
        total_h = len(lines) * (font_size + 12)
        if total_h < 600:
            break
        font_size -= 4

    lines = _wrap_text(f"\u201c{quote}\u201d", font, max_text_width, draw)
    line_h = font_size + 14
    total_h = len(lines) * line_h

    # Center vertically (leave space for author)
    author_reserve = 100 if author else 0
    start_y = (HEIGHT - total_h - author_reserve) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (WIDTH - text_w) // 2
        y = start_y + i * line_h
        # Drop shadow
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 180))
        draw.text((x, y), line, font=font, fill=GOLD)

    # Author
    if author:
        author_font = _load_font(36)
        author_text = f"\u2014 {author}"
        bbox = draw.textbbox((0, 0), author_text, font=author_font)
        aw = bbox[2] - bbox[0]
        ax = (WIDTH - aw) // 2
        ay = start_y + total_h + 30
        draw.text((ax + 1, ay + 1), author_text, font=author_font, fill=(0, 0, 0))
        draw.text((ax, ay), author_text, font=author_font, fill=(200, 165, 45))

    # Watermark
    if watermark:
        wm_font = _load_font(24)
        draw.text((WIDTH - 180, HEIGHT - 50), watermark, font=wm_font, fill=(80, 65, 20))

    # Save
    suffix = "preview" if preview else "post"
    filename = f"{suffix}_{user_id}_{uuid.uuid4().hex[:8]}.png"
    path = os.path.join(IMAGES_DIR, filename)
    img.save(path, "PNG", optimize=True)
    return path

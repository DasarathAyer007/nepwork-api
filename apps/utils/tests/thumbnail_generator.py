"""Generate job/service thumbnails by drawing dynamic text onto the
static template images in `assets/` (title, category badge, skill tags).

Used by the jobs/services factories to seed every job/service with a
distinct, on-brand thumbnail instead of a flat placeholder color.
"""

import colorsys
import hashlib
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

JOB_TEMPLATE_PATH = ASSETS_DIR / "job_template.png"
SERVICE_TEMPLATE_PATH = ASSETS_DIR / "service_template.png"

CANVAS_SIZE = (1200, 896)

# "Bold" text is faked with a text stroke -- Pillow's bundled default font
# (used below) only ships one weight, so there's no separate bold file.
BOLD_STROKE_WIDTH = 1

# Boxes were measured directly on the template images (see assets/), not
# guessed -- they line up with the placeholder shapes baked into the PNGs.
JOB_LAYOUT = {
    "title_box": (100, 150, 705, 435),
    "title_box_background": (218, 231, 239),
    "category_badge": (515, 472, 715, 528),
    "skill_pills": [
        (118, 547, 400, 599),
        (423, 547, 704, 599),
        (118, 622, 400, 673),
        (423, 622, 704, 673),
    ],
}

SERVICE_LAYOUT = {
    "title_box": (110, 105, 850, 535),
    "skill_pills": [
        (137, 540, 350, 600),
        (380, 540, 595, 600),
        (137, 620, 350, 680),
        (380, 620, 595, 680),
        (258, 700, 475, 760),
    ],
}


# ---------------------------------------------------------
# Color
# ---------------------------------------------------------


def generate_accent_color(text: str) -> tuple[int, int, int]:
    """Deterministic fallback color derived from text, used when no
    category color is available."""
    hash_value = hashlib.md5(
        text.encode("utf-8"), usedforsecurity=False
    ).hexdigest()
    hue = int(hash_value[:8], 16) / 0xFFFFFFFF
    red, green, blue = colorsys.hls_to_rgb(hue, 0.5, 0.65)
    return (int(red * 255), int(green * 255), int(blue * 255))


def hex_to_rgb(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    value = value.strip().lstrip("#")
    if len(value) != 6:
        return None
    try:
        return (
            int(value[0:2], 16),
            int(value[2:4], 16),
            int(value[4:6], 16),
        )
    except ValueError:
        return None


def resolve_accent_color(
    seed_text: str, color_hex: str | None
) -> tuple[int, int, int]:
    return hex_to_rgb(color_hex) or generate_accent_color(seed_text)


# ---------------------------------------------------------
# Text fitting helpers
# ---------------------------------------------------------


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""

    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines or [""]


def _truncate_with_ellipsis(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text

    truncated = text
    while truncated and draw.textlength(f"{truncated}…", font=font) > max_width:
        truncated = truncated[:-1]

    return f"{truncated.rstrip()}…" if truncated else "…"


def _wrap_and_cap(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    max_lines: int | None,
) -> list[str]:
    lines = _wrap_text(draw, text, font, max_width)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = _truncate_with_ellipsis(draw, lines[-1], font, max_width)
    return lines


def _fit_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_height: int,
    max_font_size: int,
    min_font_size: int,
    max_lines: int | None = None,
    line_spacing: float = 1.15,
) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, list[str], int]:
    """Pick the largest font size (within range) whose wrapped text fits
    the box; falls back to the smallest size with line-capped ellipsis."""
    for size in range(max_font_size, min_font_size - 1, -2):
        font = ImageFont.load_default(size=size)
        lines = _wrap_and_cap(draw, text, font, max_width, max_lines)
        line_height = int(size * line_spacing)
        if line_height * len(lines) <= max_height:
            return font, lines, line_height

    font = ImageFont.load_default(size=min_font_size)
    line_height = int(min_font_size * line_spacing)
    allowed_lines = max(1, max_height // line_height)
    if max_lines:
        allowed_lines = min(allowed_lines, max_lines)
    lines = _wrap_and_cap(draw, text, font, max_width, allowed_lines)
    return font, lines, line_height


def _fit_single_line(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_font_size: int,
    min_font_size: int,
) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, str]:
    for size in range(max_font_size, min_font_size - 1, -1):
        font = ImageFont.load_default(size=size)
        if draw.textlength(text, font=font) <= max_width:
            return font, text

    font = ImageFont.load_default(size=min_font_size)
    return font, _truncate_with_ellipsis(draw, text, font, max_width)


def _draw_text_centered(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
    bold: bool = False,
) -> None:
    x0, y0, x1, y1 = box
    stroke_width = BOLD_STROKE_WIDTH if bold else 0
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = x0 + ((x1 - x0) - text_width) / 2 - bbox[0]
    y = y0 + ((y1 - y0) - text_height) / 2 - bbox[1]
    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=fill,
    )


def _draw_wrapped_block(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    max_font_size: int,
    min_font_size: int,
    fill: tuple[int, int, int],
    max_lines: int | None = None,
    bold: bool = False,
    background: tuple[int, int, int] | None = None,
) -> None:
    x0, y0, x1, y1 = box
    if background is not None:
        draw.rectangle(box, fill=background)
    font, lines, line_height = _fit_wrapped_text(
        draw,
        text,
        max_width=x1 - x0,
        max_height=y1 - y0,
        max_font_size=max_font_size,
        min_font_size=min_font_size,
        max_lines=max_lines,
    )
    stroke_width = BOLD_STROKE_WIDTH if bold else 0
    for index, line in enumerate(lines):
        draw.text(
            (x0, y0 + index * line_height),
            line,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=fill,
        )


def _draw_pill(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    accent_color: tuple[int, int, int],
    max_font_size: int,
    min_font_size: int,
    bold: bool = False,
) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=(y1 - y0) // 2, fill=accent_color)
    font, fitted = _fit_single_line(
        draw,
        text.upper(),
        max_width=(x1 - x0) - 28,
        max_font_size=max_font_size,
        min_font_size=min_font_size,
    )
    _draw_text_centered(
        draw, box, fitted, font, fill=(255, 255, 255), bold=bold
    )


def _draw_skill_pills(
    draw: ImageDraw.ImageDraw,
    pill_boxes: list[tuple[int, int, int, int]],
    skills: list[str],
    accent_color: tuple[int, int, int],
) -> None:
    for box, skill in zip(pill_boxes, skills, strict=False):
        _draw_pill(
            draw,
            box,
            skill,
            accent_color,
            max_font_size=22,
            min_font_size=12,
        )


# ---------------------------------------------------------
# Canvas / output
# ---------------------------------------------------------


def _load_canvas(template_path: Path) -> Image.Image:
    image = Image.open(template_path).convert("RGB")
    if image.size != CANVAS_SIZE:
        image = image.resize(CANVAS_SIZE)
    return image


def _to_jpeg_bytes(image: Image.Image, quality: int = 90) -> bytes:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------


def generate_job_thumbnail(
    title: str,
    category_name: str,
    skills: list[str],
    color: str | None = None,
) -> bytes:
    image = _load_canvas(JOB_TEMPLATE_PATH)
    draw = ImageDraw.Draw(image)
    accent_color = resolve_accent_color(title, color)

    _draw_wrapped_block(
        draw,
        JOB_LAYOUT["title_box"],
        title,
        max_font_size=64,
        min_font_size=32,
        fill=(26, 32, 44),
        max_lines=3,
        bold=True,
        background=JOB_LAYOUT["title_box_background"],
    )

    if category_name:
        _draw_pill(
            draw,
            JOB_LAYOUT["category_badge"],
            category_name,
            accent_color,
            max_font_size=26,
            min_font_size=14,
            bold=True,
        )

    _draw_skill_pills(
        draw, JOB_LAYOUT["skill_pills"], skills or [], accent_color
    )

    return _to_jpeg_bytes(image)


def generate_service_thumbnail(
    title: str,
    skills: list[str],
    color: str | None = None,
) -> bytes:
    image = _load_canvas(SERVICE_TEMPLATE_PATH)
    draw = ImageDraw.Draw(image)
    accent_color = resolve_accent_color(title, color)

    _draw_wrapped_block(
        draw,
        SERVICE_LAYOUT["title_box"],
        title,
        max_font_size=52,
        min_font_size=28,
        fill=(38, 34, 30),
        max_lines=4,
        bold=True,
    )

    _draw_skill_pills(
        draw, SERVICE_LAYOUT["skill_pills"], skills or [], accent_color
    )

    return _to_jpeg_bytes(image)


# ---------------------------------------------------------
# Manual preview: `python -m apps.utils.tests.thumbnail_generator`
# ---------------------------------------------------------

if __name__ == "__main__":
    preview_dir = BASE_DIR / "generated_thumbnails"
    preview_dir.mkdir(parents=True, exist_ok=True)

    job_bytes = generate_job_thumbnail(
        title="Senior Backend Developer",
        category_name="Software Development",
        skills=["Python", "Django", "PostgreSQL", "REST API"],
        color="#2563eb",
    )
    (preview_dir / "job_preview.jpg").write_bytes(job_bytes)

    service_bytes = generate_service_thumbnail(
        title="Professional Logo & Brand Identity Design",
        skills=["Branding", "Illustrator", "Figma", "Typography", "Packaging"],
        color="#db2777",
    )
    (preview_dir / "service_preview.jpg").write_bytes(service_bytes)

    print(f"Wrote previews to {preview_dir}")

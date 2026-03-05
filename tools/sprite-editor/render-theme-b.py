#!/usr/bin/env python3
"""Theme B — "Pixel Block": Chunky bitmap faces, Tamagotchi/Game Boy aesthetic.

Rectangular eyes, angular mouths, grid-snapped proportions.
All activity decorations removed. Focus on expression only.

Output: sprites/theme-b/*.png
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).parent.parent.parent / "sprites" / "theme-b"
OUT.mkdir(parents=True, exist_ok=True)

ACTIVITIES = ["thinking", "conversing", "reading", "executing", "editing", "system"]
EMOTIONS = ["negative", "uneasy", "neutral", "positive", "elated"]
VARIANT_COUNTS = {"negative": 1, "uneasy": 2, "neutral": 4, "positive": 4, "elated": 1}

W, H = 200, 200
CX, CY = 100, 90
GRID = 4


def snap(v: int) -> int:
    return round(v / GRID) * GRID


def new_image() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("L", (W, H), 255)
    draw = ImageDraw.Draw(img)
    return img, draw


def draw_block(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, fill: int = 0):
    draw.rectangle([snap(x), snap(y), snap(x + w), snap(y + h)], fill=fill)


def draw_hline(draw: ImageDraw.ImageDraw, x1: int, x2: int, y: int, thickness: int = 6):
    draw.rectangle([snap(x1), snap(y), snap(x2), snap(y + thickness)], fill=0)


def draw_vline(draw: ImageDraw.ImageDraw, x: int, y1: int, y2: int, thickness: int = 6):
    draw.rectangle([snap(x), snap(y1), snap(x + thickness), snap(y2)], fill=0)


def draw_angle_line(draw: ImageDraw.ImageDraw, x1, y1, x2, y2, width=6):
    draw.line([(snap(x1), snap(y1)), (snap(x2), snap(y2))], fill=0, width=width)


# --- MOUTH ---
def draw_mouth(draw: ImageDraw.ImageDraw, emotion: str, variant: int = 0):
    cx = CX
    base_y = 136

    if emotion == "negative":
        draw_hline(draw, 50, 150, base_y + 8, 6)
        draw_vline(draw, 50, base_y, base_y + 8, 6)
        draw_vline(draw, 144, base_y, base_y + 8, 6)

    elif emotion == "uneasy":
        if variant == 0:
            draw_hline(draw, 52, 148, base_y, 6)
            draw_vline(draw, 52, base_y, base_y + 10, 6)
        else:
            draw_hline(draw, 56, 144, base_y, 6)
            draw_vline(draw, 138, base_y, base_y + 10, 6)

    elif emotion == "neutral":
        if variant == 0:
            draw_hline(draw, 52, 148, base_y, 6)
        elif variant == 1:
            draw_hline(draw, 56, 144, base_y, 6)
        elif variant == 2:
            draw_hline(draw, 48, 100, base_y, 6)
            draw_hline(draw, 100, 152, base_y + 4, 6)
        else:
            draw_hline(draw, 48, 96, base_y + 2, 6)
            draw_hline(draw, 104, 152, base_y + 2, 6)

    elif emotion == "positive":
        draw_hline(draw, 48, 152, base_y + 16, 6)
        if variant == 0:
            draw_vline(draw, 48, base_y, base_y + 16, 6)
            draw_vline(draw, 146, base_y, base_y + 16, 6)
        elif variant == 1:
            draw_vline(draw, 48, base_y + 4, base_y + 16, 6)
            draw_vline(draw, 146, base_y + 4, base_y + 16, 6)
        elif variant == 2:
            draw_vline(draw, 52, base_y, base_y + 16, 6)
            draw_vline(draw, 142, base_y, base_y + 16, 6)
        else:
            draw_vline(draw, 44, base_y + 2, base_y + 16, 6)
            draw_vline(draw, 150, base_y + 2, base_y + 16, 6)

    elif emotion == "elated":
        draw_hline(draw, 40, 160, base_y + 20, 6)
        draw_vline(draw, 40, base_y, base_y + 20, 6)
        draw_vline(draw, 154, base_y, base_y + 20, 6)
        draw_hline(draw, 40, 160, base_y, 6)


# --- EYES ---
def draw_eyes(draw: ImageDraw.ImageDraw, emotion: str, activity: str, variant: int = 0):
    lx, ly = 44, 60
    rx, ry = 120, 60
    ew, eh = 28, 28

    if activity == "thinking":
        ly, ry = 56, 56
    elif activity == "reading":
        ly, ry = 68, 68
        eh = 20
    elif activity == "editing":
        lx, rx = 40, 116
        ly, ry = 64, 64
    elif activity == "executing":
        lx, rx = 48, 116

    lx += (variant % 2) * 4
    rx += (variant % 2) * 4

    if emotion == "negative":
        ew, eh = 24, 20
    elif emotion == "uneasy":
        ew, eh = 26, 24
    elif emotion == "elated":
        ew, eh = 32, 32

    draw_block(draw, lx, ly, ew, eh)
    draw_block(draw, rx, ry, ew, eh)

    glint_w, glint_h = 8, 8
    if emotion == "negative":
        glint_w, glint_h = 6, 6
    elif emotion == "elated":
        glint_w, glint_h = 10, 10

    if emotion != "negative":
        draw_block(draw, lx + ew - glint_w - 2, ly + 2, glint_w, glint_h, fill=255)
        draw_block(draw, rx + ew - glint_w - 2, ry + 2, glint_w, glint_h, fill=255)

    if emotion == "negative":
        draw_angle_line(draw, lx - 8, ly - 16, lx + ew + 4, ly - 6, 6)
        draw_angle_line(draw, rx + ew + 8, ry - 16, rx - 4, ry - 6, 6)

    if emotion == "uneasy":
        draw_angle_line(draw, lx - 4, ly - 12, lx + ew, ly - 18, 5)
        draw_angle_line(draw, rx, ry - 18, rx + ew + 4, ry - 12, 5)

    if emotion == "elated":
        for bx, by in [(lx - 16, ly - 8), (rx + ew + 4, ry - 8)]:
            draw_block(draw, bx, by, 8, 8)
            draw_block(draw, bx + 4, by - 4, 8, 8)


# --- SLEEPING ---
def draw_sleeping(draw: ImageDraw.ImageDraw):
    lx, ly = 44, 72
    rx, ry = 120, 72
    draw_hline(draw, lx, lx + 28, ly, 6)
    draw_hline(draw, rx, rx + 28, ry, 6)
    draw_hline(draw, 80, 120, 144, 6)


def save_1bit(img: Image.Image, path: Path):
    bw = img.convert("1", dither=Image.Dither.NONE)
    bw.save(path)


# --- GENERATE ---
count = 0

for activity in ACTIVITIES:
    for emotion in EMOTIONS:
        vc = VARIANT_COUNTS[emotion]
        for v in range(vc):
            img, draw = new_image()
            draw_eyes(draw, emotion, activity, v)
            draw_mouth(draw, emotion, v)

            filename = f"{activity}_{emotion}_{v}.png"
            save_1bit(img, OUT / filename)
            count += 1

img, draw = new_image()
draw_sleeping(draw)
save_1bit(img, OUT / "sleeping_0.png")
count += 1

print(f"Theme B: Rendered {count} sprites to {OUT}/")

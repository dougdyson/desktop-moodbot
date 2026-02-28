#!/usr/bin/env python3
"""Render all 73 mood sprites as 200x200 1-bit PNGs.

Uses the same face design system as generate-baseline.js but renders
directly to PNG via Pillow for use by the moodbot server.

Output: sprites/assets/*.png
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).parent.parent.parent / "sprites" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

ACTIVITIES = ["thinking", "conversing", "reading", "executing", "editing", "system"]
EMOTIONS = ["negative", "uneasy", "neutral", "positive", "elated"]
VARIANT_COUNTS = {"negative": 1, "uneasy": 2, "neutral": 4, "positive": 4, "elated": 1}

W, H = 200, 200


def new_image() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("L", (W, H), 255)
    draw = ImageDraw.Draw(img)
    return img, draw


def draw_circle(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int,
                fill: int = None, outline: int = None, width: int = 1):
    bbox = [cx - r, cy - r, cx + r, cy + r]
    if fill is not None and outline is not None:
        draw.ellipse(bbox, fill=fill, outline=outline, width=width)
    elif fill is not None:
        draw.ellipse(bbox, fill=fill)
    elif outline is not None:
        draw.ellipse(bbox, outline=outline, width=width)


def draw_ellipse(draw: ImageDraw.ImageDraw, cx: int, cy: int, rx: int, ry: int,
                 fill: int = None, outline: int = None, width: int = 1):
    bbox = [cx - rx, cy - ry, cx + rx, cy + ry]
    if fill is not None and outline is not None:
        draw.ellipse(bbox, fill=fill, outline=outline, width=width)
    elif fill is not None:
        draw.ellipse(bbox, fill=fill)
    elif outline is not None:
        draw.ellipse(bbox, outline=outline, width=width)


def bezier_points(p0, p1, p2, steps=30):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts


def draw_bezier(draw: ImageDraw.ImageDraw, p0, p1, p2, width=4):
    pts = bezier_points(p0, p1, p2)
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=0, width=width)


def draw_line(draw: ImageDraw.ImageDraw, x1, y1, x2, y2, width=3):
    draw.line([(x1, y1), (x2, y2)], fill=0, width=width)


# --- MOUTH ---
def draw_mouth(draw: ImageDraw.ImageDraw, emotion: str, variant: int = 0):
    cx = 100
    base_y = 128

    if emotion == "negative":
        draw_bezier(draw, (72, base_y - 2), (cx, base_y - 25), (128, base_y - 2), 4)

    elif emotion == "uneasy":
        if variant == 0:
            draw_bezier(draw, (78, base_y), (cx, base_y - 12), (122, base_y + 3), 4)
        else:
            draw_bezier(draw, (75, base_y + 2), (cx - 5, base_y - 10), (125, base_y), 4)

    elif emotion == "neutral":
        if variant == 0:
            draw_line(draw, 82, base_y, 118, base_y, 3)
        elif variant == 1:
            draw_bezier(draw, (80, base_y), (cx, base_y + 5), (120, base_y), 3)
        elif variant == 2:
            draw_bezier(draw, (80, base_y), (cx, base_y - 4), (120, base_y), 3)
        else:
            draw_bezier(draw, (85, base_y - 2), (cx, base_y + 6), (115, base_y - 2), 3)

    elif emotion == "positive":
        if variant == 0:
            draw_bezier(draw, (70, 125), (cx, 155), (130, 125), 4)
        elif variant == 1:
            draw_bezier(draw, (72, 123), (cx, 150), (128, 123), 4)
        elif variant == 2:
            draw_bezier(draw, (75, 126), (cx, 148), (125, 126), 4)
        else:
            draw_bezier(draw, (73, 122), (cx, 152), (127, 122), 4)

    elif emotion == "elated":
        draw_bezier(draw, (65, 118), (cx, 162), (135, 118), 5)


# --- EYES ---
def draw_eyes(draw: ImageDraw.ImageDraw, emotion: str, activity: str, variant: int = 0):
    lx, ly = 72, 80
    rx, ry = 128, 80
    eye_r = 8
    glint_r = 3

    if activity == "thinking":
        lx, ly = 75, 75
        rx, ry = 131, 75
    elif activity == "reading":
        ly, ry = 85, 85
    elif activity == "editing":
        lx, ly = 70, 83
        rx, ry = 126, 83
    elif activity == "executing":
        lx, rx = 76, 124

    lx += (variant % 2) * 2
    rx += (variant % 2) * 2

    if emotion == "negative":
        eye_r = 6
        glint_r = 2
    elif emotion == "uneasy":
        eye_r = 7
    elif emotion == "elated":
        eye_r = 10
        glint_r = 3

    # eyes
    draw_circle(draw, lx, ly, eye_r, fill=0)
    draw_circle(draw, rx, ry, eye_r, fill=0)

    # half-lids for reading
    if activity == "reading":
        draw_bezier(draw, (lx - eye_r - 2, ly - 2), (lx, ly - eye_r - 4), (lx + eye_r + 2, ly - 2), 3)
        draw_bezier(draw, (rx - eye_r - 2, ry - 2), (rx, ry - eye_r - 4), (rx + eye_r + 2, ry - 2), 3)

    # glints (skip for negative)
    if emotion != "negative":
        draw_circle(draw, lx + 3, ly - 3, glint_r, fill=255)
        draw_circle(draw, rx + 3, ry - 3, glint_r, fill=255)

    # angry brows for negative
    if emotion == "negative":
        draw_line(draw, lx - 10, ly - 16, lx + 8, ly - 12, 3)
        draw_line(draw, rx + 10, ry - 16, rx - 8, ry - 12, 3)

    # worried brows for uneasy
    if emotion == "uneasy":
        draw_line(draw, lx - 8, ly - 14, lx + 6, ly - 16, 2)
        draw_line(draw, rx - 6, ry - 16, rx + 8, ry - 14, 2)

    # sparkles for elated
    if emotion == "elated":
        draw_line(draw, lx - 16, ly - 10, lx - 12, ly - 14, 2)
        draw_line(draw, lx - 16, ly - 14, lx - 12, ly - 10, 2)
        draw_line(draw, rx + 12, ry - 10, rx + 16, ry - 14, 2)
        draw_line(draw, rx + 12, ry - 14, rx + 16, ry - 10, 2)


# --- ACTIVITY DECORATIONS ---
def draw_activity_decor(draw: ImageDraw.ImageDraw, activity: str, variant: int = 0):
    if activity == "thinking":
        draw_circle(draw, 155, 50, 12, outline=0, width=3)
        draw_circle(draw, 143, 68, 6, outline=0, width=2)
        draw_circle(draw, 137 + variant, 80, 3, fill=0)

    elif activity == "conversing":
        draw_line(draw, 135, 125, 148, 118, 2)
        draw_line(draw, 135, 130, 150, 128, 2)
        draw_line(draw, 135, 135, 148, 138, 2)

    elif activity == "reading":
        if variant < 2:
            draw_line(draw, 45, 150, 95, 150, 2)
            draw_line(draw, 45, 158, 85, 158, 2)
            draw_line(draw, 45, 166, 90, 166, 2)
        else:
            draw_line(draw, 50, 152, 90, 152, 2)
            draw_line(draw, 110, 152, 155, 152, 2)
            draw_line(draw, 50, 160, 85, 160, 2)
            draw_line(draw, 115, 160, 150, 160, 2)

    elif activity == "executing":
        draw_line(draw, 28, 155, 40, 163, 3)
        draw_line(draw, 28, 171, 40, 163, 3)
        draw_line(draw, 45, 156, 45, 170, 2)

    elif activity == "editing":
        draw_line(draw, 30, 55, 45, 40, 3)
        draw_line(draw, 45, 40, 48, 43, 3)
        draw_line(draw, 48, 43, 33, 58, 3)
        draw_line(draw, 33, 58, 30, 55, 3)
        draw_line(draw, 28, 60, 30, 55, 2)

    elif activity == "system":
        draw_circle(draw, 160, 40, 10, outline=0, width=2)
        draw_circle(draw, 160, 40, 4, fill=0)
        draw_circle(draw, 160, 26, 2, fill=0)
        draw_circle(draw, 160, 54, 2, fill=0)
        draw_circle(draw, 146, 40, 2, fill=0)
        draw_circle(draw, 174, 40, 2, fill=0)


# --- SLEEPING ---
def draw_sleeping(draw: ImageDraw.ImageDraw):
    draw_bezier(draw, (58, 85), (72, 95), (86, 85), 4)
    draw_bezier(draw, (114, 85), (128, 95), (142, 85), 4)
    draw_bezier(draw, (88, 130), (100, 138), (112, 130), 3)

    # Z shapes
    draw_line(draw, 142, 52, 158, 52, 3)
    draw_line(draw, 158, 52, 142, 68, 3)
    draw_line(draw, 142, 68, 158, 68, 3)

    draw_line(draw, 155, 36, 166, 36, 2)
    draw_line(draw, 166, 36, 155, 47, 2)
    draw_line(draw, 155, 47, 166, 47, 2)

    draw_line(draw, 163, 23, 171, 23, 2)
    draw_line(draw, 171, 23, 163, 31, 2)
    draw_line(draw, 163, 31, 171, 31, 2)


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
            draw_activity_decor(draw, activity, v)

            filename = f"{activity}_{emotion}_{v}.png"
            save_1bit(img, OUT / filename)
            count += 1

# Sleeping
img, draw = new_image()
draw_sleeping(draw)
save_1bit(img, OUT / "sleeping_0.png")
count += 1

print(f"Rendered {count} sprites to {OUT}/")

# List a few for verification
import os
files = sorted(os.listdir(OUT))
print(f"\nFiles: {len(files)}")
for f in files[:5]:
    size = (OUT / f).stat().st_size
    print(f"  {f} ({size} bytes)")
print(f"  ... and {len(files) - 5} more")

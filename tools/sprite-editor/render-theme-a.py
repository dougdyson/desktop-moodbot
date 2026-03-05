#!/usr/bin/env python3
"""Theme A — "Big Round": Scaled-up rounded faces, eyes + mouth only.

Same bezier/circle style as original but face fills ~70% of canvas.
All activity decorations removed. Focus on expression only.

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
CX, CY = 100, 84


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


def bezier_points(p0, p1, p2, steps=40):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts


def draw_bezier(draw: ImageDraw.ImageDraw, p0, p1, p2, width=6):
    pts = bezier_points(p0, p1, p2)
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=0, width=width)


def draw_line(draw: ImageDraw.ImageDraw, x1, y1, x2, y2, width=4):
    draw.line([(x1, y1), (x2, y2)], fill=0, width=width)


# --- MOUTH ---
def draw_mouth(draw: ImageDraw.ImageDraw, emotion: str, variant: int = 0):
    cx = CX
    base_y = 134

    if emotion == "negative":
        draw_bezier(draw, (45, base_y + 5), (cx, base_y - 30), (155, base_y + 5), 6)

    elif emotion == "uneasy":
        if variant == 0:
            draw_bezier(draw, (50, base_y + 2), (cx, base_y - 16), (150, base_y + 6), 6)
        else:
            draw_bezier(draw, (48, base_y + 4), (cx - 5, base_y - 14), (152, base_y), 6)

    elif emotion == "neutral":
        if variant == 0:
            draw_line(draw, 55, base_y, 145, base_y, 5)
        elif variant == 1:
            draw_bezier(draw, (52, base_y), (cx, base_y + 10), (148, base_y), 5)
        elif variant == 2:
            draw_bezier(draw, (52, base_y), (cx, base_y - 8), (148, base_y), 5)
        else:
            draw_bezier(draw, (58, base_y - 3), (cx, base_y + 12), (142, base_y - 3), 5)

    elif emotion == "positive":
        if variant == 0:
            draw_bezier(draw, (40, base_y - 8), (cx, base_y + 45), (160, base_y - 8), 6)
        elif variant == 1:
            draw_bezier(draw, (44, base_y - 10), (cx, base_y + 40), (156, base_y - 10), 6)
        elif variant == 2:
            draw_bezier(draw, (48, base_y - 6), (cx, base_y + 38), (152, base_y - 6), 6)
        else:
            draw_bezier(draw, (42, base_y - 12), (cx, base_y + 42), (158, base_y - 12), 6)

    elif emotion == "elated":
        draw_bezier(draw, (35, base_y - 14), (cx, base_y + 55), (165, base_y - 14), 7)


# --- EYES ---
def draw_eyes(draw: ImageDraw.ImageDraw, emotion: str, activity: str, variant: int = 0):
    lx, ly = 58, 72
    rx, ry = 142, 72
    eye_r = 16
    glint_r = 5

    if activity == "thinking":
        lx, ly = 62, 66
        rx, ry = 146, 66
    elif activity == "reading":
        ly, ry = 78, 78
    elif activity == "editing":
        lx, ly = 55, 76
        rx, ry = 139, 76
    elif activity == "executing":
        lx, rx = 62, 138

    lx += (variant % 2) * 3
    rx += (variant % 2) * 3

    if emotion == "negative":
        eye_r = 12
        glint_r = 4
    elif emotion == "uneasy":
        eye_r = 14
    elif emotion == "elated":
        eye_r = 20
        glint_r = 6

    draw_circle(draw, lx, ly, eye_r, fill=0)
    draw_circle(draw, rx, ry, eye_r, fill=0)

    if activity == "reading":
        draw_bezier(draw, (lx - eye_r - 3, ly - 3), (lx, ly - eye_r - 6), (lx + eye_r + 3, ly - 3), 5)
        draw_bezier(draw, (rx - eye_r - 3, ry - 3), (rx, ry - eye_r - 6), (rx + eye_r + 3, ry - 3), 5)

    if emotion != "negative":
        draw_circle(draw, lx + 5, ly - 5, glint_r, fill=255)
        draw_circle(draw, rx + 5, ry - 5, glint_r, fill=255)

    if emotion == "negative":
        draw_line(draw, lx - 18, ly - 26, lx + 14, ly - 20, 5)
        draw_line(draw, rx + 18, ry - 26, rx - 14, ry - 20, 5)

    if emotion == "uneasy":
        draw_line(draw, lx - 14, ly - 22, lx + 10, ly - 26, 4)
        draw_line(draw, rx - 10, ry - 26, rx + 14, ry - 22, 4)

    if emotion == "elated":
        for dx, dy, sign in [(-22, -14, -1), (22, -14, 1)]:
            bx = (lx if sign == -1 else rx) + dx
            by = (ly if sign == -1 else ry) + dy
            draw_line(draw, bx - 5, by - 5, bx + 5, by + 5, 3)
            draw_line(draw, bx - 5, by + 5, bx + 5, by - 5, 3)


# --- SLEEPING ---
def draw_sleeping(draw: ImageDraw.ImageDraw):
    lx, ly = 58, 76
    rx, ry = 142, 76
    draw_bezier(draw, (lx - 22, ly), (lx, ly + 16), (lx + 22, ly), 6)
    draw_bezier(draw, (rx - 22, ry), (rx, ry + 16), (rx + 22, ry), 6)
    draw_bezier(draw, (80, 139), (100, 149), (120, 139), 5)


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

print(f"Theme A: Rendered {count} sprites to {OUT}/")

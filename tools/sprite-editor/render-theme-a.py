#!/usr/bin/env python3
"""Theme A v2 — "Big Round" with 8-channel design vocabulary.

Eye socket + pupil system for gaze direction.
Asymmetric mouths for uncertainty.
Open mouth shapes for engagement.
Sparse eyebrows for personality.

See sprite-ideas.md for design vocabulary reference.

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

GAZE = {
    "thinking":   (4, -4),
    "conversing": (0, -1),
    "reading":    (-1, 4),
    "executing":  (0, 1),
    "editing":    (-3, 3),
    "system":     (2, 0),
}


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


def draw_open_mouth(draw: ImageDraw.ImageDraw, left_x: int, right_x: int,
                    lip_y: int, upper_ctrl_y: int, lower_ctrl_y: int, width: int = 5):
    cx = CX
    upper_pts = bezier_points((left_x, lip_y), (cx, upper_ctrl_y), (right_x, lip_y))
    lower_pts = bezier_points((left_x, lip_y), (cx, lower_ctrl_y), (right_x, lip_y))
    polygon = upper_pts + lower_pts[::-1]
    draw.polygon(polygon, fill=0)
    draw_bezier(draw, (left_x, lip_y), (cx, upper_ctrl_y), (right_x, lip_y), width)
    draw_bezier(draw, (left_x, lip_y), (cx, lower_ctrl_y), (right_x, lip_y), width)


# --- EYES (socket + pupil system) ---
def draw_eyes(draw: ImageDraw.ImageDraw, emotion: str, activity: str, variant: int = 0):
    lx, ly = 58, 72
    rx, ry = 142, 72
    socket_r = 20
    pupil_r = 10
    glint_r = 4
    outline_w = 3

    if activity == "thinking":
        lx, ly = 60, 69
        rx, ry = 144, 69
    elif activity == "reading":
        ly, ry = 75, 75
    elif activity == "editing":
        lx, ly = 56, 74
        rx, ry = 140, 74
    elif activity == "executing":
        lx, rx = 60, 140

    if emotion == "negative":
        socket_r = 16
        pupil_r = 8
        glint_r = 3
    elif emotion == "uneasy":
        socket_r = 18
        pupil_r = 9
    elif emotion == "elated":
        socket_r = 24
        pupil_r = 12
        glint_r = 5

    lx += (variant % 2) * 3
    rx += (variant % 2) * 3

    gaze_dx, gaze_dy = GAZE.get(activity, (0, 0))

    half_lid = False
    lid_drop = 0
    if activity == "reading":
        half_lid = True
        lid_drop = socket_r - 2
    if emotion == "positive" and variant == 3:
        half_lid = True
        lid_drop = socket_r - 4

    for ex, ey in [(lx, ly), (rx, ry)]:
        draw_circle(draw, ex, ey, socket_r, fill=0)
        draw_circle(draw, ex, ey, socket_r - outline_w, fill=255)

        px = ex + gaze_dx
        py = ey + gaze_dy
        draw_circle(draw, px, py, pupil_r, fill=0)

        if emotion != "negative":
            draw_circle(draw, px + 3, py - 3, glint_r, fill=255)

        if half_lid:
            lid_y = ey - socket_r + lid_drop
            draw.rectangle(
                [ex - socket_r - 2, ey - socket_r - 5, ex + socket_r + 2, lid_y],
                fill=255
            )
            draw_bezier(
                draw,
                (ex - socket_r, lid_y),
                (ex, lid_y - 5),
                (ex + socket_r, lid_y),
                4
            )

    if emotion == "negative":
        draw_line(draw, lx - 18, ly - 28, lx + 14, ly - 22, 5)
        draw_line(draw, rx + 18, ry - 28, rx - 14, ry - 22, 5)

    if emotion == "uneasy" and variant == 0:
        draw_line(draw, lx - 14, ly - 24, lx + 10, ly - 28, 4)
        draw_line(draw, rx - 10, ry - 28, rx + 14, ry - 24, 4)

    if emotion == "neutral" and variant == 3:
        draw_bezier(draw, (rx - 14, ry - 26), (rx, ry - 34), (rx + 14, ry - 26), 4)

    if emotion == "positive" and variant == 2:
        draw_bezier(draw, (rx - 14, ry - 26), (rx, ry - 34), (rx + 14, ry - 26), 4)

    if emotion == "elated":
        draw_bezier(draw, (lx - 16, ly - 28), (lx, ly - 36), (lx + 16, ly - 28), 4)
        draw_bezier(draw, (rx - 16, ry - 28), (rx, ry - 36), (rx + 16, ry - 28), 4)
        for dx, dy, sign in [(-26, -18, -1), (26, -18, 1)]:
            bx = (lx if sign == -1 else rx) + dx
            by = (ly if sign == -1 else ry) + dy
            draw_line(draw, bx - 5, by - 5, bx + 5, by + 5, 3)
            draw_line(draw, bx - 5, by + 5, bx + 5, by - 5, 3)


# --- MOUTH ---
def draw_mouth(draw: ImageDraw.ImageDraw, emotion: str, variant: int = 0):
    cx = CX
    base_y = 134

    if emotion == "negative":
        draw_bezier(draw, (45, base_y + 5), (cx, base_y - 30), (155, base_y + 5), 6)

    elif emotion == "uneasy":
        if variant == 0:
            draw_bezier(draw, (50, base_y + 8), (75, base_y - 6), (cx, base_y + 2), 6)
            draw_bezier(draw, (cx, base_y + 2), (125, base_y - 2), (150, base_y - 2), 6)
        else:
            draw_bezier(draw, (52, base_y + 4), (cx - 10, base_y - 4), (cx, base_y + 1), 5)
            draw_bezier(draw, (cx, base_y + 1), (cx + 10, base_y + 3), (148, base_y - 1), 5)

    elif emotion == "neutral":
        if variant == 0:
            draw_line(draw, 55, base_y, 145, base_y, 5)
        elif variant == 1:
            draw_bezier(draw, (52, base_y), (cx, base_y + 10), (148, base_y), 5)
        elif variant == 2:
            draw_bezier(draw, (52, base_y), (cx, base_y - 8), (148, base_y), 5)
        else:
            draw_bezier(draw, (58, base_y - 2), (cx, base_y + 10), (142, base_y - 2), 5)

    elif emotion == "positive":
        if variant == 0:
            draw_bezier(draw, (42, base_y - 8), (cx, base_y + 42), (158, base_y - 8), 6)
        elif variant == 1:
            draw_open_mouth(draw, 44, 156, base_y - 6, base_y + 30, base_y + 50, 5)
        elif variant == 2:
            draw_bezier(draw, (48, base_y - 2), (75, base_y + 20), (cx, base_y + 10), 6)
            draw_bezier(draw, (cx, base_y + 10), (125, base_y + 35), (152, base_y - 10), 6)
        else:
            draw_bezier(draw, (38, base_y - 10), (cx, base_y + 48), (162, base_y - 10), 7)

    elif emotion == "elated":
        draw_open_mouth(draw, 35, 165, base_y - 12, base_y + 36, base_y + 58, 6)


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

print(f"Theme A v2: Rendered {count} sprites to {OUT}/")

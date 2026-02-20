"""Bitmap encoder for M5Stack CoreInk e-ink display.

Converts 200x200 PNG/BMP images to 1-bit packed format and base64 encodes
them for transmission over HTTP JSON.

Wire format: row-major, MSB first, 1 = black, 0 = white.
200px wide = 25 bytes per row. 200 rows = 5000 bytes total.
Base64 encoded: ~6668 characters.
"""

import base64
from pathlib import Path


DISPLAY_WIDTH = 200
DISPLAY_HEIGHT = 200
BYTES_PER_ROW = DISPLAY_WIDTH // 8  # 25
BITMAP_SIZE = BYTES_PER_ROW * DISPLAY_HEIGHT  # 5000


def png_to_bitmap(path: Path) -> bytes:
    """Convert a PNG/BMP image to 1-bit packed bitmap bytes.

    Uses only stdlib. Reads the image via basic PNG decoding or falls back
    to Pillow if available. The image must be exactly 200x200.

    Returns:
        5000 bytes of packed 1-bit bitmap data (row-major, MSB first).

    Raises:
        ValueError: If the image is not 200x200.
        ImportError: If Pillow is not installed.
    """
    try:
        from PIL import Image
    except ImportError:
        raise ImportError(
            "Pillow is required for sprite encoding: pip install Pillow"
        )

    img = Image.open(path)

    if img.size != (DISPLAY_WIDTH, DISPLAY_HEIGHT):
        raise ValueError(
            f"Image must be {DISPLAY_WIDTH}x{DISPLAY_HEIGHT}, "
            f"got {img.size[0]}x{img.size[1]}"
        )

    # Convert to 1-bit (black and white) with dithering disabled
    bw = img.convert("1", dither=Image.Dither.NONE)

    packed = bytearray(BITMAP_SIZE)
    pixels = bw.load()

    for y in range(DISPLAY_HEIGHT):
        for x in range(DISPLAY_WIDTH):
            # PIL 1-bit: 0 = black, 255 = white
            # Our format: 1 = black, 0 = white
            if pixels[x, y] == 0:
                byte_idx = y * BYTES_PER_ROW + x // 8
                bit_idx = 7 - (x % 8)  # MSB first
                packed[byte_idx] |= 1 << bit_idx

    return bytes(packed)


def bitmap_to_base64(bitmap: bytes) -> str:
    """Base64 encode packed bitmap bytes for JSON transport."""
    return base64.b64encode(bitmap).decode("ascii")


def encode_sprite(path: Path) -> str:
    """Full pipeline: PNG file → base64 encoded 1-bit bitmap string."""
    bitmap = png_to_bitmap(path)
    return bitmap_to_base64(bitmap)


def base64_to_bitmap(encoded: str) -> bytes:
    """Decode base64 bitmap back to packed bytes (for testing/verification)."""
    return base64.b64decode(encoded)

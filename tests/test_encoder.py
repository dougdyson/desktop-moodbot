import base64
from pathlib import Path

import pytest

from sprites.encoder import (
    BITMAP_SIZE,
    BYTES_PER_ROW,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    base64_to_bitmap,
    bitmap_to_base64,
    encode_sprite,
    png_to_bitmap,
)


PIL = pytest.importorskip("PIL", reason="Pillow required for encoder tests")
from PIL import Image


def _make_png(tmp_path, width=200, height=200, color="white", name="test.png"):
    """Create a simple solid-color PNG for testing."""
    img = Image.new("RGB", (width, height), color)
    path = tmp_path / name
    img.save(path)
    return path


def _make_checkerboard(tmp_path, name="checker.png"):
    """Create a 200x200 checkerboard (8px squares) for bit-level testing."""
    img = Image.new("1", (200, 200), 1)  # white background
    pixels = img.load()
    for y in range(200):
        for x in range(200):
            if (x // 8 + y // 8) % 2 == 0:
                pixels[x, y] = 0  # black
    path = tmp_path / name
    img.save(path)
    return path


class TestPngToBitmap:
    def test_all_white_image(self, tmp_path):
        path = _make_png(tmp_path, color="white")
        bitmap = png_to_bitmap(path)
        assert len(bitmap) == BITMAP_SIZE
        assert bitmap == b"\x00" * BITMAP_SIZE

    def test_all_black_image(self, tmp_path):
        path = _make_png(tmp_path, color="black")
        bitmap = png_to_bitmap(path)
        assert len(bitmap) == BITMAP_SIZE
        assert bitmap == b"\xff" * BITMAP_SIZE

    def test_wrong_dimensions_raises(self, tmp_path):
        path = _make_png(tmp_path, width=100, height=100)
        with pytest.raises(ValueError, match="200x200"):
            png_to_bitmap(path)

    def test_wrong_width_raises(self, tmp_path):
        path = _make_png(tmp_path, width=201, height=200)
        with pytest.raises(ValueError, match="200x200"):
            png_to_bitmap(path)

    def test_bitmap_size_constants(self):
        assert DISPLAY_WIDTH == 200
        assert DISPLAY_HEIGHT == 200
        assert BYTES_PER_ROW == 25
        assert BITMAP_SIZE == 5000

    def test_single_black_pixel(self, tmp_path):
        """Top-left pixel black, rest white."""
        img = Image.new("RGB", (200, 200), "white")
        img.putpixel((0, 0), (0, 0, 0))
        path = tmp_path / "one_pixel.png"
        img.save(path)

        bitmap = png_to_bitmap(path)
        # First byte should have MSB set (0x80)
        assert bitmap[0] == 0x80
        # Rest should be zero
        assert all(b == 0 for b in bitmap[1:])

    def test_first_row_all_black(self, tmp_path):
        """First row black, rest white."""
        img = Image.new("RGB", (200, 200), "white")
        for x in range(200):
            img.putpixel((x, 0), (0, 0, 0))
        path = tmp_path / "first_row.png"
        img.save(path)

        bitmap = png_to_bitmap(path)
        # First 25 bytes should all be 0xFF
        assert bitmap[:BYTES_PER_ROW] == b"\xff" * BYTES_PER_ROW
        # Rest should be zero
        assert bitmap[BYTES_PER_ROW:] == b"\x00" * (BITMAP_SIZE - BYTES_PER_ROW)

    def test_checkerboard_pattern(self, tmp_path):
        path = _make_checkerboard(tmp_path)
        bitmap = png_to_bitmap(path)
        assert len(bitmap) == BITMAP_SIZE
        # Not all zeros, not all ones
        assert bitmap != b"\x00" * BITMAP_SIZE
        assert bitmap != b"\xff" * BITMAP_SIZE


class TestBase64RoundTrip:
    def test_roundtrip_white(self, tmp_path):
        path = _make_png(tmp_path, color="white")
        bitmap = png_to_bitmap(path)
        encoded = bitmap_to_base64(bitmap)
        decoded = base64_to_bitmap(encoded)
        assert decoded == bitmap

    def test_roundtrip_black(self, tmp_path):
        path = _make_png(tmp_path, color="black")
        bitmap = png_to_bitmap(path)
        encoded = bitmap_to_base64(bitmap)
        decoded = base64_to_bitmap(encoded)
        assert decoded == bitmap

    def test_encode_sprite_full_pipeline(self, tmp_path):
        path = _make_png(tmp_path, color="black")
        encoded = encode_sprite(path)
        assert isinstance(encoded, str)
        # Verify it's valid base64
        decoded = base64.b64decode(encoded)
        assert len(decoded) == BITMAP_SIZE


class TestGrayscaleConversion:
    def test_gray_image_converts_to_bw(self, tmp_path):
        """Gray pixels should threshold to black or white."""
        img = Image.new("L", (200, 200), 128)  # mid-gray
        path = tmp_path / "gray.png"
        img.save(path)

        bitmap = png_to_bitmap(path)
        assert len(bitmap) == BITMAP_SIZE
        # Should be all one value (all black or all white after threshold)
        unique = set(bitmap)
        assert len(unique) == 1

    def test_rgba_image_works(self, tmp_path):
        """RGBA images should convert correctly."""
        img = Image.new("RGBA", (200, 200), (0, 0, 0, 255))
        path = tmp_path / "rgba.png"
        img.save(path)

        bitmap = png_to_bitmap(path)
        assert len(bitmap) == BITMAP_SIZE
        assert bitmap == b"\xff" * BITMAP_SIZE

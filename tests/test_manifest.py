from pathlib import Path

import pytest

from sprites.manifest import SpriteManifest


PIL = pytest.importorskip("PIL", reason="Pillow required for manifest tests")
from PIL import Image


def _make_sprite(assets_dir, name, color="black"):
    """Create a 200x200 test sprite PNG."""
    assets_dir.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (200, 200), color)
    path = assets_dir / name
    img.save(path)
    return path


class TestSpriteManifest:
    def test_lookup_returns_none_when_no_assets(self, tmp_path):
        manifest = SpriteManifest(assets_dir=tmp_path / "empty")
        result = manifest.lookup("thinking", "neutral", 0)
        assert result is None

    def test_lookup_exact_match(self, tmp_path):
        assets = tmp_path / "assets"
        _make_sprite(assets, "thinking_neutral_0.png")
        manifest = SpriteManifest(assets_dir=assets)

        result = manifest.lookup("thinking", "neutral", 0)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_lookup_variant_fallback(self, tmp_path):
        """Should fall back to variant 0 when requested variant missing."""
        assets = tmp_path / "assets"
        _make_sprite(assets, "thinking_neutral_0.png")
        manifest = SpriteManifest(assets_dir=assets)

        result = manifest.lookup("thinking", "neutral", 3)
        assert result is not None

    def test_lookup_activity_fallback(self, tmp_path):
        """Should fall back to thinking when requested activity missing."""
        assets = tmp_path / "assets"
        _make_sprite(assets, "thinking_positive_0.png")
        manifest = SpriteManifest(assets_dir=assets)

        # No conversing_positive sprite, should fall back to thinking_positive
        result = manifest.lookup("conversing", "positive", 0)
        assert result is not None

    def test_lookup_no_fallback_when_nothing_exists(self, tmp_path):
        assets = tmp_path / "assets"
        _make_sprite(assets, "thinking_neutral_0.png")
        manifest = SpriteManifest(assets_dir=assets)

        # No sprite for negative at all
        result = manifest.lookup("conversing", "negative", 0)
        assert result is None

    def test_sleeping_sprite(self, tmp_path):
        assets = tmp_path / "assets"
        _make_sprite(assets, "sleeping_0.png")
        manifest = SpriteManifest(assets_dir=assets)

        result = manifest.lookup("thinking", "neutral", 0, sleeping=True)
        assert result is not None

    def test_sleeping_falls_through_when_no_sleeping_sprite(self, tmp_path):
        assets = tmp_path / "assets"
        _make_sprite(assets, "thinking_neutral_0.png")
        manifest = SpriteManifest(assets_dir=assets)

        # No sleeping sprite, should fall through to normal lookup
        result = manifest.lookup("thinking", "neutral", 0, sleeping=True)
        assert result is not None

    def test_cache_works(self, tmp_path):
        assets = tmp_path / "assets"
        _make_sprite(assets, "thinking_neutral_0.png")
        manifest = SpriteManifest(assets_dir=assets)

        result1 = manifest.lookup("thinking", "neutral", 0)
        result2 = manifest.lookup("thinking", "neutral", 0)
        assert result1 == result2
        assert len(manifest._cache) == 1

    def test_clear_cache(self, tmp_path):
        assets = tmp_path / "assets"
        _make_sprite(assets, "thinking_neutral_0.png")
        manifest = SpriteManifest(assets_dir=assets)

        manifest.lookup("thinking", "neutral", 0)
        assert len(manifest._cache) == 1
        manifest.clear_cache()
        assert len(manifest._cache) == 0

    def test_list_sprites(self, tmp_path):
        assets = tmp_path / "assets"
        _make_sprite(assets, "thinking_neutral_0.png")
        _make_sprite(assets, "conversing_positive_0.png")
        manifest = SpriteManifest(assets_dir=assets)

        sprites = manifest.list_sprites()
        assert len(sprites) == 2
        assert "conversing_positive_0.png" in sprites
        assert "thinking_neutral_0.png" in sprites

    def test_list_sprites_empty(self, tmp_path):
        manifest = SpriteManifest(assets_dir=tmp_path / "empty")
        assert manifest.list_sprites() == []

    def test_sprite_exists(self, tmp_path):
        assets = tmp_path / "assets"
        _make_sprite(assets, "thinking_neutral_0.png")
        manifest = SpriteManifest(assets_dir=assets)

        assert manifest.sprite_exists("thinking", "neutral", 0) is True
        assert manifest.sprite_exists("thinking", "neutral", 1) is False

    def test_different_sprites_different_bitmaps(self, tmp_path):
        assets = tmp_path / "assets"
        _make_sprite(assets, "thinking_neutral_0.png", color="black")
        _make_sprite(assets, "thinking_positive_0.png", color="white")
        manifest = SpriteManifest(assets_dir=assets)

        neutral = manifest.lookup("thinking", "neutral", 0)
        positive = manifest.lookup("thinking", "positive", 0)
        assert neutral != positive

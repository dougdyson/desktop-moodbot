"""Sprite manifest: maps (activity, emotion, variant) → sprite file.

The manifest defines which visual states exist and resolves them to PNG files
in the assets directory. States without dedicated sprites fall back through:
  1. Same activity + emotion, variant 0
  2. "thinking" + same emotion, variant 0 (default activity)
  3. "sleeping" sprite (if sleeping)
  4. None (no bitmap served — device uses preloaded default)

File naming convention:
    {activity}_{emotion}_{variant}.png
    e.g. thinking_neutral_0.png, conversing_positive_1.png, sleeping_0.png

Sprite spec (for art generation):
    - Canvas: 200×200 pixels
    - Color: black and white only (1-bit, no grayscale)
    - Format: PNG (will be converted to packed bitmap)
    - Character should be centered with ~10px margin
"""

from pathlib import Path
from typing import Optional

from .encoder import encode_sprite

# Default assets directory (sibling to this file)
_DEFAULT_ASSETS_DIR = Path(__file__).parent / "assets"


class SpriteManifest:
    def __init__(self, assets_dir: Optional[Path] = None):
        self.assets_dir = assets_dir or _DEFAULT_ASSETS_DIR
        self._cache: dict[str, str] = {}

    def lookup(self, activity: str, emotion: str, variant: int,
               sleeping: bool = False) -> Optional[str]:
        """Resolve a mood state to a base64-encoded bitmap string.

        Returns None if no matching sprite file exists.
        """
        if sleeping:
            result = self._try_encode("sleeping_0")
            if result:
                return result

        # Try exact match: activity_emotion_variant.png
        result = self._try_encode(f"{activity}_{emotion}_{variant}")
        if result:
            return result

        # Fallback: variant 0
        if variant != 0:
            result = self._try_encode(f"{activity}_{emotion}_0")
            if result:
                return result

        # Fallback: thinking as default activity
        if activity != "thinking":
            result = self._try_encode(f"thinking_{emotion}_0")
            if result:
                return result

        return None

    def _try_encode(self, stem: str, ext: str = "png") -> Optional[str]:
        """Try to load and encode a sprite file, using cache."""
        # Normalize the key
        key = f"{stem}.{ext}" if "." not in stem else stem
        if not key.endswith(f".{ext}"):
            key = f"{key}.{ext}"

        if key in self._cache:
            return self._cache[key]

        path = self.assets_dir / key
        if not path.exists():
            return None

        try:
            encoded = encode_sprite(path)
            self._cache[key] = encoded
            return encoded
        except (ValueError, ImportError, OSError):
            return None

    def list_sprites(self) -> list[str]:
        """Return all PNG filenames in the assets directory."""
        if not self.assets_dir.exists():
            return []
        return sorted(p.name for p in self.assets_dir.glob("*.png"))

    def clear_cache(self) -> None:
        """Clear the encoded bitmap cache (e.g. after sprite files change)."""
        self._cache.clear()

    def sprite_exists(self, activity: str, emotion: str, variant: int) -> bool:
        """Check if a specific sprite file exists (without encoding it)."""
        name = f"{activity}_{emotion}_{variant}.png"
        return (self.assets_dir / name).exists()

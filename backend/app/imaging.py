"""Derivatives of uploaded designs. The original file never leaves the server.

- preview: downscaled (max 1600 px), corner-watermarked, kept on disk.
- scrambled view: the preview cut into a grid and shuffled per request, so no
  usable image URL or file exists on the client; the canvas reassembles it.
- thumbnail: small watermarked image for wallets displaying the certificate.

This raises the cost of casual saving and generic scrapers; it cannot stop a
determined attacker taking screenshots, which is what on-chain proof covers.
"""

from __future__ import annotations

import io
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

PREVIEW_MAX = 1600
THUMBNAIL_MAX = 512
GRID = 8
TILE_PAD = 2  # extruded border per sprite cell, so lossy compression never bleeds between tiles

Image.MAX_IMAGE_PIXELS = 120_000_000  # guard against decompression bombs


def make_preview(original: Path, destination: Path, mark: str) -> bool:
    """Write the preview; False when the upload is not a raster image."""
    try:
        with Image.open(original) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return False
    image.thumbnail((PREVIEW_MAX, PREVIEW_MAX), Image.Resampling.LANCZOS)
    _watermark(image, mark)
    image.save(destination, "WEBP", quality=86, method=6)
    return True


def _watermark(image: Image.Image, mark: str) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    size = max(11, image.width // 60)
    font = ImageFont.load_default(size=size)
    box = draw.textbbox((0, 0), mark, font=font)
    margin = size
    position = (image.width - (box[2] - box[0]) - margin, image.height - (box[3] - box[1]) - margin * 1.5)
    draw.text(position, mark, font=font, fill=(255, 255, 255, 34))


@dataclass(frozen=True)
class ScrambledView:
    webp: bytes
    width: int
    height: int
    cols: int
    rows: int
    pad: int
    order: list[int]  # order[tile] = slot where that tile sits in the shuffled sprite


def scrambled_view(preview: Path, grid: int = GRID, max_side: int = PREVIEW_MAX) -> ScrambledView:
    with Image.open(preview) as image:
        image = image.convert("RGB")
    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    tile_w, tile_h = image.width // grid, image.height // grid
    width, height = tile_w * grid, tile_h * grid
    image = image.crop((0, 0, width, height))

    tiles = grid * grid
    sprite_slots = list(range(tiles))
    random.SystemRandom().shuffle(sprite_slots)  # sprite_slots[tile] = where it goes in the sprite
    pad = TILE_PAD
    cell_w, cell_h = tile_w + 2 * pad, tile_h + 2 * pad
    sprite = Image.new("RGB", (cell_w * grid, cell_h * grid))
    for tile, slot in enumerate(sprite_slots):
        sx, sy = (tile % grid) * tile_w, (tile // grid) * tile_h
        dx, dy = (slot % grid) * cell_w, (slot // grid) * cell_h
        piece = image.crop((sx, sy, sx + tile_w, sy + tile_h))
        sprite.paste(piece.resize((cell_w, cell_h), Image.Resampling.NEAREST), (dx, dy))
        sprite.paste(piece, (dx + pad, dy + pad))

    buffer = io.BytesIO()
    sprite.save(buffer, "WEBP", quality=88)
    return ScrambledView(buffer.getvalue(), width, height, grid, grid, pad, sprite_slots)


def thumbnail(preview: Path) -> bytes:
    with Image.open(preview) as image:
        image = image.convert("RGB")
    image.thumbnail((THUMBNAIL_MAX, THUMBNAIL_MAX), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "WEBP", quality=80)
    return buffer.getvalue()

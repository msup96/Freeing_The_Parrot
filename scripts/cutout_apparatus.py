"""Isolate apparatus from ivory studio background (exact pixels, no regeneration)."""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


def sample_background(rgb: np.ndarray) -> np.ndarray:
    h, w, _ = rgb.shape
    patches = [
        rgb[0:50, 0:50],
        rgb[0:50, w - 50 : w],
        rgb[h - 50 : h, 0:50],
        rgb[h - 50 : h, w - 50 : w],
    ]
    return np.median(np.concatenate([p.reshape(-1, 3) for p in patches], axis=0), axis=0)


def color_distance(rgb: np.ndarray, bg: np.ndarray) -> np.ndarray:
    diff = rgb.astype(np.float32) - bg.astype(np.float32)
    return np.sqrt(np.sum(diff * diff, axis=-1))


def flood_background(dist: np.ndarray, threshold: float) -> np.ndarray:
    h, w = dist.shape
    bg = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()

    def try_seed(y: int, x: int) -> None:
        if 0 <= y < h and 0 <= x < w and not bg[y, x] and dist[y, x] <= threshold:
            bg[y, x] = True
            q.append((y, x))

    for x in range(w):
        try_seed(0, x)
        try_seed(h - 1, x)
    for y in range(h):
        try_seed(y, 0)
        try_seed(y, w - 1)

    while q:
        y, x = q.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and not bg[ny, nx] and dist[ny, nx] <= threshold:
                bg[ny, nx] = True
                q.append((ny, nx))
    return bg


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    src = root / "static" / "images" / "ftp2-apparatus-hero.jpg"
    dst = root / "static" / "images" / "ftp2-apparatus-hero.png"

    img = Image.open(src).convert("RGB")
    rgb = np.array(img)
    h, w, _ = rgb.shape
    bg_color = sample_background(rgb)
    dist = color_distance(rgb, bg_color)

    # Connected background from edges (ivory studio)
    is_bg = flood_background(dist, threshold=32.0)

    # Soft alpha at boundary
    alpha = np.zeros((h, w), dtype=np.float32)
    alpha[is_bg] = 0.0
    edge = (~is_bg) & (dist < 48.0)
    alpha[~is_bg] = 1.0
    alpha[edge] = np.clip((dist[edge] - 30.0) / 18.0, 0.15, 1.0)

    # Remove floor contact shadow (outside flood but still near-bg dark neutrals)
    y0 = int(h * 0.84)
    shadow_zone = np.zeros((h, w), dtype=bool)
    shadow_zone[y0:, :] = True
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    neutral_dark = (
        (r < 195) & (g < 195) & (b < 195) & (np.abs(r.astype(int) - g.astype(int)) < 30)
    )
    alpha[shadow_zone & neutral_dark & (dist < 60)] = 0.0

    rgba = np.dstack([rgb, (np.clip(alpha, 0, 1) * 255).astype(np.uint8)])
    out = Image.fromarray(rgba, "RGBA")
    out.save(dst, optimize=True)
    a = rgba[:, :, 3]
    print(f"Wrote {dst} ({w}x{h})")
    print(f"transparent={(a < 8).sum()} / {a.size} bbox={out.getbbox()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

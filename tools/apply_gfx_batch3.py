#!/usr/bin/env python3
"""Graphics translation batch 3: status screens.

Covers the top-screen idol status panel (rank / image level / trend image),
the fan-count rank screen (U_IDOLRANK), the idol profile label, and the
save/load kanji name plates.

Special handling beyond the batch1/2 machinery:
  - PAIRS: some texts span two records drawn flush on screen (kanji names
    水谷絵|理, genre plates ダンス系…|ce).  The text renders once across a
    combined canvas which is then sliced back into the member records.
  - erase: plate records keep their background; JP glyph pixels (white
    fill / dark outline) are repainted with the row's dominant color
    (preserves the vertical gradient), protecting a 2px frame.
  - comma: the counter kanji 万 (x10000) becomes "," -- numbers are
    zero-padded 4 digits after it, so 1万1799 reads 1,1799 = 11,799.
  - blank: counter suffixes 人/組 have no room for English -> transparent.
  - U_IDOLRANK_VFX rank-up letters pop in one tile at a time:
    ア イ ド ル ラ ン ク U P  ->  I D O L R A NK (U P originals kept).

Run:  python -X utf8 tools/apply_gfx_batch3.py   (then tools/gld_import.py)
"""
import os
import sys
from collections import Counter

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from gld_export import parse_gld, decode
from apply_gfx_batch1 import (sample_style, fit_size, draw_fitted, SRC, OUT)

LEVEL_TITLES = [
    "Amateur", "Novice Idol", "Unknown Idol", "Niche Favorite",
    "One to Watch", "Must-See Idol", "Talk of the Town", "About to Break",
    "Breakout Idol", "Popular Idol", "Hit Idol", "Super Idol",
    "Charisma Idol", "National Idol", "Historic Idol", "Idol Legend",
]

# (gld, idx, text, group|None) -- text-only records, fresh transparent draw
SIMPLE = [
    ("PARAM_IDOL_IMAGE_LEVEL", 0, "IDOL RANK", "small_label"),
    ("PARAM_IDOL_IMAGE_LEVEL", 13, "IMAGE LEVEL", "small_label"),
    *[("PARAM_IDOL_IMAGE_LEVEL", 24 + i, LEVEL_TITLES[i], "level_title")
      for i in range(16)],
    ("SAVELOAD_CHOICE", 16, "Ryo Akizuki", "sl_name"),
    ("SAVELOAD_CHOICE", 17, "Ryo Akizuki", "sl_name"),
    ("SAVELOAD_CHOICE", 18, "Ryo Akizuki", "sl_name"),
    ("SAVELOAD_CHOICE", 19, "Ai Hidaka", "sl_name"),
    ("SAVELOAD_CHOICE", 20, "Ai Hidaka", "sl_name"),
    ("SAVELOAD_CHOICE", 21, "Ai Hidaka", "sl_name"),
    ("SAVELOAD_CHOICE", 22, "Eri Mizutani", "sl_name"),
    ("SAVELOAD_CHOICE", 23, "Eri Mizutani", "sl_name"),
    ("SAVELOAD_CHOICE", 24, "Eri Mizutani", "sl_name"),
    ("SAVELOAD_CHOICE", 25, "IMAGE LEVEL", "sl_label"),
    ("SAVELOAD_CHOICE", 26, "IDOL RANK", "sl_label"),
    ("U_IDOLDATAMENU_LABEL", 0, "IDOL PROFILE", None),
    ("U_IDOLRANK", 14, "FAN COUNT", None),
    ("U_IDOLRANK", 18, "TO NEXT RANK", None),
    ("U_IDOLRANK", 21, "1,000,000+", "fans"),
    ("U_IDOLRANK", 23, "700,000+", "fans"),
    ("U_IDOLRANK", 25, "300,000+", "fans"),
    ("U_IDOLRANK", 27, "100,000+", "fans"),
    ("U_IDOLRANK", 29, "10,000+", "fans"),
    ("U_IDOLRANK", 43, "RANK", None),
    ("U_IDOLRANK", 44, "RANK", None),
    ("U_IDOLRANK", 53, "IDOL RANK UP!", None),
    ("U_IDOLRANK_VFX", 2, "I", "vfx"),
    ("U_IDOLRANK_VFX", 3, "D", "vfx"),
    ("U_IDOLRANK_VFX", 4, "O", "vfx"),
    ("U_IDOLRANK_VFX", 5, "L", "vfx"),
    ("U_IDOLRANK_VFX", 6, "R", "vfx"),
    ("U_IDOLRANK_VFX", 7, "A", "vfx"),
    ("U_IDOLRANK_VFX", 8, "NK", None),
]

# (gld, (indices drawn flush left-to-right), text, erase_plate, group)
PAIRS = [
    ("PARAM_IDOL_IMAGE_LEVEL", (7, 8), "Ai Hidaka", False, "param_name"),
    ("PARAM_IDOL_IMAGE_LEVEL", (9, 10), "Eri Mizutani", False, "param_name"),
    ("PARAM_IDOL_IMAGE_LEVEL", (11, 12), "Ryo Akizuki", False, "param_name"),
    ("PARAM_BOOM_RANK_NAME", (0, 1), "DANCE", True, "boom_name"),
    ("PARAM_BOOM_RANK_NAME", (2, 3), "VISUAL", True, "boom_name"),
    ("PARAM_BOOM_RANK_NAME", (4, 5), "VOCAL", True, "boom_name"),
    ("PARAM_BOOM_RANK_GROUND", (5,), "TREND IMAGE", True, None),
]

COMMAS = [("PARAM_BOOM_RANK_NUMBER", 13), ("U_IDOLRANK", 12)]   # 万
BLANKS = [("PARAM_BOOM_RANK_GROUND", 6), ("U_IDOLRANK", 13)]    # 組, 人


def erase_plate_text(im):
    """Repaint JP glyph pixels (white fill / dark outline) on an opaque
    plate with the row-dominant mid-tone, keeping the vertical gradient
    and a 2px protected frame (plate borders/highlights)."""
    px = im.load()
    W, H = im.size
    rowbg = []
    for y in range(H):
        cnt = Counter()
        for x in range(W):
            r, g, b, a = px[x, y]
            if a >= 160 and 100 <= (r + g + b) / 3 <= 215:
                cnt[(r, g, b)] += 1
        rowbg.append(cnt.most_common(1)[0][0] if cnt else None)
    prev = next((c for c in rowbg if c), (128, 128, 128))
    for y in range(H):
        if rowbg[y] is None:
            rowbg[y] = prev
        prev = rowbg[y]

    def near_edge(x, y):
        for dy in (-2, -1, 0, 1, 2):
            for dx in (-2, -1, 0, 1, 2):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < W and 0 <= ny < H) or px[nx, ny][3] < 64:
                    return True
        return False

    for y in range(H):
        for x in range(W):
            r, g, b, a = px[x, y]
            if a < 100:
                continue
            lum = (r + g + b) / 3
            if (lum > 215 or lum < 100) and not near_edge(x, y):
                px[x, y] = rowbg[y] + (a,)


def combined(cache, gld, idxs):
    pixels, palette, recs = cache[gld]
    ims = [decode(pixels, palette, recs[i]) for i in idxs]
    W = sum(im.width for im in ims)
    H = max(im.height for im in ims)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = 0
    for im in ims:
        canvas.alpha_composite(im, (x, 0))
        x += im.width
    return canvas, ims


def pair_style(canvas, erase):
    if erase:
        # plate: white text; outline = darkest solid cluster
        px = canvas.load()
        colors = Counter(px[x, y][:3] for y in range(canvas.height)
                         for x in range(canvas.width) if px[x, y][3] >= 160)
        return (255, 255, 255), min(colors, key=lambda c: sum(c))
    return sample_style(canvas)


def load(cache, gld):
    if gld not in cache:
        data = open(os.path.join(SRC, gld + ".GLD"), "rb").read()
        cache[gld] = parse_gld(data)
    return cache[gld]


def main():
    os.makedirs(OUT, exist_ok=True)
    cache = {}
    for gld, idx, text, g in SIMPLE:
        load(cache, gld)
    for gld, idxs, text, erase, g in PAIRS:
        load(cache, gld)

    # shared font size per group (see batch1 GROUPS note)
    sizes = {}
    for gld, idx, text, g in SIMPLE:
        if not g:
            continue
        pixels, palette, recs = cache[gld]
        orig = decode(pixels, palette, recs[idx])
        stroke = 1 if sample_style(orig)[1] else 0
        pad = 2 if orig.width > 40 else 0
        s = fit_size(text, orig.width - 2 * pad, orig.height, stroke)
        sizes[g] = min(sizes.get(g, 99), s)
    for gld, idxs, text, erase, g in PAIRS:
        if not g:
            continue
        canvas, _ = combined(cache, gld, idxs)
        s = fit_size(text, canvas.width - 4, canvas.height - 2, 1)
        sizes[g] = min(sizes.get(g, 99), s)

    for gld, idx, text, g in SIMPLE:
        pixels, palette, recs = cache[gld]
        rec = recs[idx]
        orig = decode(pixels, palette, rec)
        fill, outline = sample_style(orig)
        stroke = 1 if outline else 0
        pad = 2 if orig.width > 40 else 0
        box = (pad, 0, orig.width - pad, orig.height)
        size = sizes.get(g) or fit_size(text, box[2] - box[0],
                                        orig.height, stroke)
        im = Image.new("RGBA", orig.size, (0, 0, 0, 0))
        draw_fitted(im, text, box, fill, outline, stroke, size)
        im.save(os.path.join(OUT, f"{gld}_{idx:02d}_f{rec.fmt}.png"))
        print(f"{gld}#{idx} <- {text}")

    for gld, idxs, text, erase, g in PAIRS:
        pixels, palette, recs = cache[gld]
        canvas, ims = combined(cache, gld, idxs)
        fill, outline = pair_style(canvas, erase)
        if erase:
            erase_plate_text(canvas)
        size = sizes.get(g) or fit_size(text, canvas.width - 4,
                                        canvas.height - 2, 1)
        draw_fitted(canvas, text, (2, 1, canvas.width - 2, canvas.height - 1),
                    fill, outline, 1, size)
        x = 0
        for i, im in zip(idxs, ims):
            part = canvas.crop((x, 0, x + im.width, im.height))
            part.save(os.path.join(OUT, f"{gld}_{i:02d}_f{recs[i].fmt}.png"))
            x += im.width
        print(f"{gld}#{idxs} <- {text}")

    for gld, idx in COMMAS:
        pixels, palette, recs = load(cache, gld)
        rec = recs[idx]
        orig = decode(pixels, palette, rec)
        fill, outline = sample_style(orig)
        im = Image.new("RGBA", orig.size, (0, 0, 0, 0))
        draw_fitted(im, ",", (0, 0, rec.w, rec.h), fill, outline,
                    1 if outline else 0, rec.h + 4, ypos=0.72)
        im.save(os.path.join(OUT, f"{gld}_{idx:02d}_f{rec.fmt}.png"))
        print(f"{gld}#{idx} <- ,")

    for gld, idx in BLANKS:
        pixels, palette, recs = load(cache, gld)
        rec = recs[idx]
        Image.new("RGBA", (rec.w, rec.h), (0, 0, 0, 0)).save(
            os.path.join(OUT, f"{gld}_{idx:02d}_f{rec.fmt}.png"))
        print(f"{gld}#{idx} <- (blank)")

    n = len(SIMPLE) + sum(len(p[1]) for p in PAIRS) + len(COMMAS) + len(BLANKS)
    print(f"{n} images rendered into {OUT}")


if __name__ == "__main__":
    main()

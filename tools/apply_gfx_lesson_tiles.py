#!/usr/bin/env python3
"""Graphics: vocal-lesson kana tiles -> romaji (enables playing the
fill-in-the-lyrics minigame without reading kana).

D_EPANEL_MOJI_MNG (answer panels, black glyphs) and D_MEASURE_MOJI_MNG
(sentence line, white glyphs w/ dark outline) each hold 81 tiles in
gojuon order.  LESVOICETABLE* string data stays Japanese -- the game
looks glyphs up by kana code, so only the tile art changes (the earlier
attempt to put ASCII in the string data drew blanks; see memory).

Index 46 = the long-vowel bar, already fine -> skipped.
Small kana (72-80) render at ~72% size, like the kana convention.
ji/zu vs dji/dzu keeps ぢ/づ distinguishable on the panels.

Run:  python -X utf8 tools/apply_gfx_lesson_tiles.py  (then gld_import.py)
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from gld_export import parse_gld, decode
from apply_gfx_batch1 import SRC, OUT, fit_size, draw_fitted

ROMAJI = (
    "a i u e o ka ki ku ke ko sa shi su se so ta chi tsu te to "
    "na ni nu ne no ha hi fu he ho ma mi mu me mo ya yu yo "
    "ra ri ru re ro wa wo n - "
    "ga gi gu ge go za ji zu ze zo da dji dzu de do "
    "ba bi bu be bo pa pi pu pe po "
    "a i u e o tsu ya yu yo").split()
assert len(ROMAJI) == 81
SMALL = range(72, 81)          # small kana tiles
SKIP = {46}                    # long-vowel bar: original art already reads

# (gld, fill, outline) -- styles are constant per sheet
SHEETS = [
    ("D_EPANEL_MOJI_MNG", (32, 32, 32), None),
    ("D_MEASURE_MOJI_MNG", (255, 255, 255), (32, 32, 48)),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    for gld, fill, outline in SHEETS:
        data = open(os.path.join(SRC, gld + ".GLD"), "rb").read()
        pixels, palette, recs = parse_gld(data)
        stroke = 1 if outline else 0
        size = min(fit_size(ROMAJI[i], recs[i].w, recs[i].h, stroke)
                   for i in range(81) if i not in SKIP and i not in SMALL)
        small = max(8, round(size * 0.72))
        for i in range(81):
            if i in SKIP:
                continue
            rec = recs[i]
            im = Image.new("RGBA", (rec.w, rec.h), (0, 0, 0, 0))
            draw_fitted(im, ROMAJI[i], (0, 0, rec.w, rec.h), fill, outline,
                        stroke, small if i in SMALL else size)
            im.save(os.path.join(OUT, f"{gld}_{i:02d}_f{rec.fmt}.png"))
        print(f"{gld}: 80 tiles, size {size} (small kana {small})")


if __name__ == "__main__":
    main()

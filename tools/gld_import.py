#!/usr/bin/env python3
"""Re-import edited PNGs into GLD graphics files.

Reads gfx/edited/F_AGL/<GLDNAME>_<NN>_f<FMT>.png (same naming as
gld_export.py output, same pixel size as the original image), re-encodes
each into the matching image record of unpacked/F_AGL/<GLDNAME>.GLD and
writes the patched file to patched/F_AGL/<GLDNAME>.GLD.  build_rom.py picks
those up when rebuilding the F_AGL archive.

The original palette of each record is kept: every edited pixel is mapped
to the nearest palette color (and quantized alpha for A3I5/A5I3).  Draw
with colors sampled from the original export and results are exact.

Usage:
  python gld_import.py                 process all edited PNGs
  python gld_import.py <png> [...]     process specific PNGs
"""
import os, re, struct, sys

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from gld_export import parse_gld, get_pal

EDITED = os.path.join("gfx", "edited", "F_AGL")
SRC = os.path.join("unpacked", "F_AGL")
OUT = os.path.join("patched", "F_AGL")

NAME_RE = re.compile(r"^(.*)_(\d\d)_f(\d+)\.png$", re.I)


def nearest(pal, rgb):
    best, bd = 0, 1 << 30
    r, g, b = rgb
    for i, (pr, pg, pb) in enumerate(pal):
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < bd:
            best, bd = i, d
    return best


def encode_into(gld, img, png_path):
    """Re-encode png into record `img` of GLD byte array (in place)."""
    im = Image.open(png_path).convert("RGBA")
    if im.size != (img.w, img.h):
        raise ValueError(
            f"{png_path}: size {im.size} != original {(img.w, img.h)}"
        )
    pix_size = struct.unpack_from("<I", gld, 0x0C)[0]
    pal_base = 0x20 + pix_size
    stride = img.stride
    xo, yo = img.xoff, img.yoff
    base = 0x20 + img.pix_off
    px = im.load()

    def pal(n):
        return get_pal(gld[pal_base : pal_base + struct.unpack_from("<I", gld, 0x18)[0]],
                       img.pal_off, n)

    if img.fmt in (1, 6):  # A3I5 / A5I3
        ncol, abits = (32, 3) if img.fmt == 1 else (8, 5)
        colors = pal(ncol)
        amax = (1 << abits) - 1
        cache = {}
        for y in range(img.h):
            row = base + (yo + y) * stride + xo
            for x in range(img.w):
                r, g, b, a = px[x, y]
                aq = (a * amax + 127) // 255
                if aq == 0:
                    gld[row + x] = 0
                    continue
                key = (r, g, b)
                idx = cache.get(key)
                if idx is None:
                    idx = cache[key] = nearest(colors, key)
                gld[row + x] = (aq << (8 - abits)) | idx
    elif img.fmt in (2, 3, 4):  # I2 / I4 / I8, color 0 = transparent
        ncol = {2: 4, 3: 16, 4: 256}[img.fmt]
        colors = pal(ncol)[1:]  # index 0 reserved for transparent
        bpp = {2: 2, 3: 4, 4: 8}[img.fmt]
        row_bytes = stride * bpp // 8
        cache = {}
        for y in range(img.h):
            rowvals = []
            for x in range(img.w):
                r, g, b, a = px[x, y]
                if a < 128:
                    rowvals.append(0)
                    continue
                key = (r, g, b)
                idx = cache.get(key)
                if idx is None:
                    idx = cache[key] = nearest(colors, key) + 1
                rowvals.append(idx)
            row = base + (yo + y) * row_bytes
            if img.fmt == 4:
                gld[row + xo : row + xo + img.w] = bytes(rowvals)
            else:
                per = 8 // bpp
                for x in range(img.w):
                    bx = (xo + x) // per
                    shift = ((xo + x) % per) * bpp
                    v = gld[row + bx]  # keep bits of neighboring pixels
                    v &= ~(((1 << bpp) - 1) << shift) & 0xFF
                    v |= rowvals[x] << shift
                    gld[row + bx] = v
    elif img.fmt == 7:  # direct 16-bit
        for y in range(img.h):
            row = base + ((yo + y) * stride + xo) * 2
            for x in range(img.w):
                r, g, b, a = px[x, y]
                v = ((a >= 128) << 15) | ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)
                struct.pack_into("<H", gld, row + x * 2, v)
    else:
        raise ValueError(f"unhandled format {img.fmt}")


def main():
    if len(sys.argv) > 1:
        pngs = sys.argv[1:]
    else:
        pngs = [os.path.join(EDITED, f) for f in sorted(os.listdir(EDITED))
                if f.lower().endswith(".png")]
    by_gld = {}
    for p in pngs:
        m = NAME_RE.match(os.path.basename(p))
        if not m:
            raise SystemExit(f"bad name (want <GLD>_<NN>_f<FMT>.png): {p}")
        by_gld.setdefault(m.group(1), []).append((int(m.group(2)), p))

    os.makedirs(OUT, exist_ok=True)
    for name, items in sorted(by_gld.items()):
        src = os.path.join(SRC, name + ".GLD")
        gld = bytearray(open(src, "rb").read())
        _, _, recs = parse_gld(bytes(gld))
        for idx, p in items:
            encode_into(gld, recs[idx], p)
        out = os.path.join(OUT, name + ".GLD")
        open(out, "wb").write(gld)
        print(f"{out}: {len(items)} image(s) patched")


if __name__ == "__main__":
    main()

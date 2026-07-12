#!/usr/bin/env python3
"""Export GLD graphics (F_AGL etc.) to PNG.

GLD container ("\\0DLG" magic):
  0x00 magic "\\0DLG", 0x04 version (2,2)
  0x08 u32 fileSize
  0x0c u32 pixelDataSize     (same value repeated at 0x14)
  0x10 u32 zero
  0x18 u32 paletteBlockSize
  0x1c u32 imageCount
  0x20 pixel data (per-image offsets from the records)
  0x20+pixelDataSize                palette block (BGR555 u16s)
  0x20+pixelDataSize+paletteSize    imageCount records (28 bytes in
      version 2.2 files, 24 bytes in older 1.2 files):
      u32 pixOff (rel. to 0x20)
      u16 palOff (bytes into palette block)
      u16 format (NDS texture format: 1=A3I5 2=I2 3=I4 4=I8 6=A5I3 7=direct)
      u16 width, u16 height        (real crop size)
      u16 S, u16 T                 (block size codes: row stride = 8<<S pixels)
      u16 xoff, u16 yoff           (crop offset in pixels within the block;
                                    several records can share one pixel block)
      u32 ?, u16 ?, u16 ?          (unknown / draw metadata)

Usage:
  python gld_export.py file.GLD [outdir]       one file -> outdir/<name>_NN.png
  python gld_export.py --all [srcdir outdir]   default unpacked/F_AGL -> gfx/F_AGL
  python gld_export.py --sheet <srcdir> <out.png>  contact sheet of every image
"""
import os, struct, sys

from PIL import Image

REC_SIZE = 28


def pow2ceil(n):
    p = 8
    while p < n:
        p <<= 1
    return p


def bgr555(v):
    r = (v & 0x1F) << 3
    g = ((v >> 5) & 0x1F) << 3
    b = ((v >> 10) & 0x1F) << 3
    return (r | r >> 5, g | g >> 5, b | b >> 5)


class GldImage:
    __slots__ = ("index", "pix_off", "pal_off", "fmt", "w", "h", "s", "t",
                 "xoff", "yoff", "extra")

    @property
    def stride(self):
        return 8 << self.s


def parse_gld(data):
    if len(data) < 0x20 or data[:4] != b"\x00DLG":
        raise ValueError("not a GLD file")
    pix_size = struct.unpack_from("<I", data, 0x0C)[0]
    pal_size = struct.unpack_from("<I", data, 0x18)[0]
    count = struct.unpack_from("<I", data, 0x1C)[0]
    pixels = data[0x20 : 0x20 + pix_size]
    palette = data[0x20 + pix_size : 0x20 + pix_size + pal_size]
    recs = []
    base = 0x20 + pix_size + pal_size
    rec_size = (len(data) - base) // count if count else REC_SIZE
    if rec_size not in (24, 28):
        raise ValueError(f"unexpected record size {rec_size}")
    for i in range(count):
        o = base + i * rec_size
        img = GldImage()
        img.index = i
        (img.pix_off,) = struct.unpack_from("<I", data, o)
        img.pal_off, img.fmt, img.w, img.h, img.s, img.t = struct.unpack_from(
            "<HHHHHH", data, o + 4
        )
        # 28-byte records carry the crop offset (u16 x, u16 y) at +16; the
        # older 24-byte records have other fields there and no offsets.
        if rec_size == 28:
            img.xoff, img.yoff = struct.unpack_from("<HH", data, o + 16)
        else:
            img.xoff = img.yoff = 0
        img.extra = data[o + 16 : o + rec_size]
        recs.append(img)
    return pixels, palette, recs


def get_pal(palette, off, ncolors):
    out = []
    for i in range(ncolors):
        p = off + i * 2
        if p + 2 <= len(palette):
            out.append(bgr555(struct.unpack_from("<H", palette, p)[0]))
        else:
            out.append((255, 0, 255))
    return out


def decode(pixels, palette, img):
    stride = img.stride
    w, h = img.w, img.h
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    off = img.pix_off
    xo, yo = img.xoff, img.yoff
    if img.fmt == 1:  # A3I5: 5-bit index, 3-bit alpha
        pal = get_pal(palette, img.pal_off, 32)
        for y in range(h):
            row = off + (yo + y) * stride + xo
            for x in range(w):
                b = pixels[row + x]
                a3 = b >> 5
                px[x, y] = pal[b & 0x1F] + ((a3 << 5 | a3 << 2 | a3 >> 1),)
    elif img.fmt == 6:  # A5I3: 3-bit index, 5-bit alpha
        pal = get_pal(palette, img.pal_off, 8)
        for y in range(h):
            row = off + (yo + y) * stride + xo
            for x in range(w):
                b = pixels[row + x]
                a5 = b >> 3
                px[x, y] = pal[b & 7] + ((a5 << 3 | a5 >> 2),)
    elif img.fmt == 2:  # I2: 2bpp, color 0 transparent
        pal = get_pal(palette, img.pal_off, 4)
        rb = stride // 4
        for y in range(h):
            row = off + (yo + y) * rb
            for x in range(w):
                b = pixels[row + (xo + x) // 4]
                v = (b >> (((xo + x) % 4) * 2)) & 3
                px[x, y] = pal[v] + (0 if v == 0 else 255,)
    elif img.fmt == 3:  # I4: 4bpp
        pal = get_pal(palette, img.pal_off, 16)
        rb = stride // 2
        for y in range(h):
            row = off + (yo + y) * rb
            for x in range(w):
                b = pixels[row + (xo + x) // 2]
                v = (b >> (((xo + x) % 2) * 4)) & 0xF
                px[x, y] = pal[v] + (0 if v == 0 else 255,)
    elif img.fmt == 4:  # I8: 8bpp
        pal = get_pal(palette, img.pal_off, 256)
        for y in range(h):
            row = off + (yo + y) * stride + xo
            for x in range(w):
                v = pixels[row + x]
                px[x, y] = pal[v] + (0 if v == 0 else 255,)
    elif img.fmt == 7:  # direct 16-bit, bit15 = opaque
        for y in range(h):
            row = off + ((yo + y) * stride + xo) * 2
            for x in range(w):
                v = struct.unpack_from("<H", pixels, row + x * 2)[0]
                px[x, y] = bgr555(v) + (255 if v & 0x8000 else 0,)
    else:
        raise ValueError(f"unhandled format {img.fmt}")
    return im


def export_file(path, outdir):
    data = open(path, "rb").read()
    if not data:
        return []
    pixels, palette, recs = parse_gld(data)
    name = os.path.splitext(os.path.basename(path))[0]
    os.makedirs(outdir, exist_ok=True)
    out = []
    for img in recs:
        if img.fmt & 0x8000:
            # flat window-fill rectangle, no pixel data stored
            continue
        im = decode(pixels, palette, img)
        p = os.path.join(outdir, f"{name}_{img.index:02d}_f{img.fmt}.png")
        im.save(p)
        out.append((p, img))
    return out


def main():
    args = sys.argv[1:]
    if args and args[0] == "--all":
        src = args[1] if len(args) > 1 else "unpacked/F_AGL"
        dst = args[2] if len(args) > 2 else "gfx/F_AGL"
        n_files = n_imgs = 0
        for fn in sorted(os.listdir(src)):
            if not fn.upper().endswith(".GLD"):
                continue
            try:
                res = export_file(os.path.join(src, fn), dst)
            except ValueError as e:
                print(f"{fn}: SKIP ({e})")
                continue
            if res:
                n_files += 1
                n_imgs += len(res)
        print(f"exported {n_imgs} images from {n_files} GLD files -> {dst}")
    elif args:
        res = export_file(args[0], args[1] if len(args) > 1 else "gfx")
        for p, img in res:
            print(
                f"{p}: {img.w}x{img.h} fmt={img.fmt} pal@{img.pal_off:#x} "
                f"pix@{img.pix_off:#x} extra={img.extra.hex()}"
            )
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Graphics translation batch 1: banners, title/story menu, common buttons.

For each target record this renders English text into a PNG under
gfx/edited/F_AGL/ (style colors sampled from the original image), then
gld_import.py re-encodes them into patched/F_AGL/*.GLD.

Run:  python -X utf8 tools/apply_gfx_batch1.py   (then tools/gld_import.py)
"""
import os
import sys
from collections import Counter

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from gld_export import parse_gld, decode

SRC = os.path.join("unpacked", "F_AGL")
OUT = os.path.join("gfx", "edited", "F_AGL")
FONT = "C:/Windows/Fonts/arialbd.ttf"

# (gld, rec index, text, options)
# options: caps=upper, inpaint=text sits on opaque button (repaint interior),
#          fill/outline=override sampled colors
BATCH = [
    # ---- banners ----
    ("D_AUD_FAILING", 0, "AUDITION FAILED", {}),
    ("D_START", 0, "AUDITION START", {}),
    ("D_START", 1, "AUDITION START", {"inpaint": True, "group": "aud_btn"}),
    ("D_END", 0, "AUDITION OVER", {}),
    ("D_END", 1, "AUDITION OVER", {"inpaint": True, "group": "aud_btn"}),
    ("COMMU_BAD", 0, "BAD MEMORY", {}),
    ("COMMU_GOOD", 0, "GOOD MEMORY", {}),
    ("COMMU_NORMAL", 0, "NORMAL MEMORY", {}),
    ("COMMU_PERFECT", 0, "PERFECT MEMORY", {}),
    ("LES_BAD", 0, "BAD LESSON", {}),
    ("LES_GOOD", 0, "GOOD LESSON", {}),
    ("LES_NORMAL", 1, "NORMAL LESSON", {}),
    ("LES_PERFECT", 1, "PERFECT LESSON", {}),
    ("LES_END", 0, "LESSON OVER", {}),
    ("THE_TOUCH", 1, "Touch the lower screen", {}),
    ("GET_PANEL", 0, "Got a dance panel!", {}),
    ("GET_PRESENT", 1, "A present from a fan", {}),
    # ---- title menu buttons (idle / selected / pressed) ----
    ("D_MENU_BTN_STORY", 2, "STORY", {}),
    ("D_MENU_BTN_STORY", 5, "STORY", {}),
    ("D_MENU_BTN_STORY", 6, "STORY", {}),
    ("D_MENU_BTN_STAGE", 2, "STAGE", {}),
    ("D_MENU_BTN_STAGE", 5, "STAGE", {}),
    ("D_MENU_BTN_STAGE", 6, "STAGE", {}),
    ("D_MENU_BTN_WIFI", 2, "Wi-Fi", {}),
    ("D_MENU_BTN_WIFI", 5, "Wi-Fi", {}),
    ("D_MENU_BTN_WIFI", 6, "Wi-Fi", {}),
    ("D_MENU_BTN_WIRELESS", 2, "DS WIRELESS", {}),
    ("D_MENU_BTN_WIRELESS", 5, "DS WIRELESS", {}),
    ("D_MENU_BTN_WIRELESS", 6, "DS WIRELESS", {}),
    ("D_MENU_BTN_QRC", 4, "QR CODE", {}),
    ("D_MENU_BTN_QRC", 5, "QR CODE", {}),
    ("D_MENU_BTN_QRC", 6, "QR CODE", {}),
    # ---- story (save select) menu ----
    ("D_STORY_BTN", 0, "ACTIVE IDOL", {}),
    ("D_STORY_BTN", 1, "ACTIVE IDOL", {}),
    ("D_STORY_BTN", 2, "ACTIVE IDOL", {}),
    ("D_STORY_BTN", 3, "DELETE SAVE DATA", {}),
    ("D_STORY_BTN", 4, "DELETE SAVE DATA", {}),
    ("D_STORY_BTN", 5, "DELETE SAVE DATA", {}),
    ("D_STORY_BTN", 6, "START WITH A NEW IDOL", {}),
    ("D_STORY_BTN", 7, "START WITH A NEW IDOL", {}),
    ("D_STORY_BTN", 8, "START WITH A NEW IDOL", {}),
    ("D_STORY_BTN02", 0, "ACTIVE IDOL", {}),
    ("D_STORY_BTN02", 1, "ACTIVE IDOL", {}),
    ("D_STORY_BTN02", 2, "ACTIVE IDOL", {}),
    ("D_STORY_BTN02", 3, "DELETE SAVE DATA", {}),
    ("D_STORY_BTN02", 4, "DELETE SAVE DATA", {}),
    ("D_STORY_BTN02", 5, "DELETE SAVE DATA", {}),
    ("D_STORY_BTN02", 6, "START WITH A NEW IDOL", {}),
    ("D_STORY_BTN02", 7, "START WITH A NEW IDOL", {}),
    ("D_STORY_BTN02", 8, "START WITH A NEW IDOL", {}),
    ("D_STORY_BTN02", 9, "AND THEN...", {}),
    ("D_STORY_BTN02", 10, "AND THEN...", {}),
    ("D_STORY_BTN02", 11, "AND THEN...", {}),
    # ---- common buttons ----
    ("D_COM_BTN", 0, "OK", {}), ("D_COM_BTN", 1, "OK", {}),
    ("D_COM_BTN", 2, "OK", {}), ("D_COM_BTN", 3, "OK", {}),
    ("D_COM_BTN", 4, "Back", {}), ("D_COM_BTN", 5, "Back", {}),
    ("D_COM_BTN", 6, "Back", {}), ("D_COM_BTN", 7, "Back", {}),
    ("D_COM_BTN", 8, "Close", {}), ("D_COM_BTN", 9, "Close", {}),
    ("D_COM_BTN", 10, "Close", {}), ("D_COM_BTN", 11, "Close", {}),
    ("D_COMMON_BTN", 0, "OK", {}), ("D_COMMON_BTN", 1, "OK", {}),
    ("D_COMMON_BTN", 2, "OK", {}), ("D_COMMON_BTN", 3, "OK", {}),
    ("D_COMMON_BTN", 4, "Back", {}), ("D_COMMON_BTN", 5, "Back", {}),
    ("D_COMMON_BTN", 6, "Back", {}), ("D_COMMON_BTN", 7, "Back", {}),
    ("D_COM2_BTN", 0, "Back", {}), ("D_COM2_BTN", 1, "Back", {}),
    ("D_COM2_BTN", 2, "Back", {}), ("D_COM2_BTN", 3, "Back", {}),
    ("D_COM2_BTN", 4, "Remove", {}), ("D_COM2_BTN", 5, "Remove", {}),
    ("D_COM2_BTN", 6, "Remove", {}), ("D_COM2_BTN", 7, "Remove", {}),
    ("D_OK_BTN", 0, "OK", {}), ("D_OK_BTN", 1, "OK", {}),
    ("D_OK_BTN", 2, "OK", {}), ("D_OK_BTN", 3, "OK", {}),
    ("D_BASIC_BTNMENU", 0, "Keep going", {}),
    ("D_BASIC_BTNMENU", 1, "Keep going", {}),
    ("D_BASIC_BTNMENU", 2, "Keep going", {}),
    ("D_BASIC_BTNMENU", 3, "Apply & return", {}),
    ("D_BASIC_BTNMENU", 4, "Apply & return", {}),
    ("D_BASIC_BTNMENU", 5, "Apply & return", {}),
    ("D_BASIC_BTNMENU", 6, "Return unchanged", {}),
    ("D_BASIC_BTNMENU", 7, "Return unchanged", {}),
    ("D_BASIC_BTNMENU", 8, "Return unchanged", {}),
    # ---- idol status ----
    ("IDOL_IMAGE_WND_LABEL", 0, "IMAGE LEVEL DOWN", {}),
    ("IDOL_IMAGE_WND_LABEL", 1, "IMAGE LEVEL UP", {}),
    ("IDOL_IMAGE_WND_LEVEL_01", 0, "Lv 1  Amateur", {}),
    ("IDOL_IMAGE_WND_LEVEL_02", 0, "Lv 2  Novice Idol", {}),
    ("IDOL_IMAGE_WND_LEVEL_03", 0, "Lv 3  Unknown Idol", {}),
    ("IDOL_IMAGE_WND_LEVEL_04", 0, "Lv 4  Niche Favorite", {}),
    ("IDOL_IMAGE_WND_LEVEL_05", 0, "Lv 5  One to Watch", {}),
    ("IDOL_IMAGE_WND_LEVEL_06", 0, "Lv 6  Must-See Idol", {}),
    ("IDOL_IMAGE_WND_LEVEL_07", 0, "Lv 7  Talk of the Town", {}),
    ("IDOL_IMAGE_WND_LEVEL_08", 0, "Lv 8  About to Break", {}),
    ("IDOL_IMAGE_WND_LEVEL_09", 0, "Lv 9  Breakout Idol", {}),
    ("IDOL_IMAGE_WND_LEVEL_10", 0, "Lv10  Popular Idol", {}),
    ("IDOL_IMAGE_WND_LEVEL_11", 0, "Lv11  Hit Idol", {}),
    ("IDOL_IMAGE_WND_LEVEL_12", 0, "Lv12  Super Idol", {}),
    ("IDOL_IMAGE_WND_LEVEL_13", 0, "Lv13  Charisma Idol", {}),
    ("IDOL_IMAGE_WND_LEVEL_14", 0, "Lv14  National Idol", {}),
    ("IDOL_IMAGE_WND_LEVEL_15", 0, "Lv15  Historic Idol", {}),
    ("IDOL_IMAGE_WND_LEVEL_16", 0, "Lv16  Idol Legend", {}),
]


def bucket(c):
    return (c[0] // 16, c[1] // 16, c[2] // 16)


def _dist2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def sample_style(im):
    """(fill, outline|None) sampled from an RGBA text image.

    Text graphics in this game are typically <fill color> glyphs wrapped in
    an outline or soft glow whose pixels are often SEMI-transparent, so the
    outline must be sampled below full alpha.  Fill vs outline is decided by
    which color cluster touches transparency more.
    """
    px = im.load()
    solid = Counter()   # a >= 100
    glow = Counter()    # 40 <= a < 100 (soft outline / shadow halo)
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a >= 100:
                solid[bucket((r, g, b))] += 1
            elif a >= 40:
                glow[bucket((r, g, b))] += 1
    if not solid:
        if not glow:
            return (255, 255, 255), None
        bk = glow.most_common(1)[0][0]
        return (bk[0] * 16 + 8, bk[1] * 16 + 8, bk[2] * 16 + 8), None

    def real(bk):
        return (bk[0] * 16 + 8, bk[1] * 16 + 8, bk[2] * 16 + 8)

    # two dominant, sufficiently distinct solid clusters
    ranked = solid.most_common()
    c1 = ranked[0][0]
    c2 = None
    for bk, n in ranked[1:]:
        if _dist2(real(bk), real(c1)) > 3600 and n >= max(8, ranked[0][1] // 8):
            c2 = bk
            break

    if c2 is not None:
        # the outline cluster touches transparency more often
        touch = {c1: [0, 1], c2: [0, 1]}  # [touching, total]
        for y in range(im.height):
            for x in range(im.width):
                r, g, b, a = px[x, y]
                if a < 100:
                    continue
                c = c1 if _dist2((r, g, b), real(c1)) <= _dist2(
                    (r, g, b), real(c2)) else c2
                touch[c][1] += 1
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < im.width and 0 <= ny < im.height) \
                            or px[nx, ny][3] < 40:
                        touch[c][0] += 1
                        break
        r1 = touch[c1][0] / touch[c1][1]
        r2 = touch[c2][0] / touch[c2][1]
        fill_bk, out_bk = (c1, c2) if r1 <= r2 else (c2, c1)
        return real(fill_bk), real(out_bk)

    fill = real(c1)
    # single solid color: use the glow halo as outline if present
    if glow:
        gbk = glow.most_common(1)[0][0]
        if _dist2(real(gbk), fill) > 3600:
            return fill, real(gbk)
        # halo is just antialiasing of the fill: genuinely outline-less
        return fill, None
    # no alpha information at all: guarantee some contrast
    lum = sum(fill) / 3
    if lum > 185:
        return fill, (55, 55, 65)
    if lum < 80:
        return fill, (255, 255, 255)
    return fill, None


def fit_font(draw, text, w, h, stroke):
    for size in range(min(h + 4, 40), 6, -1):
        f = ImageFont.truetype(FONT, size)
        x0, y0, x1, y1 = draw.textbbox((0, 0), text, font=f,
                                       stroke_width=stroke)
        if x1 - x0 <= w and y1 - y0 <= h:
            return f, (x0, y0, x1, y1)
    return f, (x0, y0, x1, y1)


# ---------------------------------------------------------------------------
# Uniform sizing.  GLD records are cropped to the ORIGINAL JP text, so box
# widths vary per label (オーディション wide, 休む narrow); sizing each image
# to fill its own box gave every label a different font size.  Instead,
# images that appear together on screen share a group: one font size is
# picked from box HEIGHT (uniform per group) and labels that are too wide
# for their crop are condensed horizontally, like the JP originals.
# ---------------------------------------------------------------------------
MIN_SQUEEZE = 0.60          # narrowest allowed horizontal condensation

GROUPS = {
    "aud_banner": ("D_AUD_", "D_START", "D_END"),
    "memory_banner": ("COMMU_",),
    "lesson_banner": ("LES_",),
    "title_menu": ("D_MENU_BTN_",),
    "story_menu": ("D_STORY_BTN",),
    "common_btn": ("D_COM_BTN", "D_COMMON_BTN", "D_COM2_BTN", "D_OK_BTN"),
    "basic_menu": ("D_BASIC_BTNMENU",),
    "image_label": ("IDOL_IMAGE_WND_LABEL",),
    "image_level": ("IDOL_IMAGE_WND_LEVEL",),
}


def group_of(gld, groups=GROUPS, opts=None):
    if opts and "group" in opts:
        return opts["group"]
    for g, prefixes in groups.items():
        if any(gld.startswith(p) for p in prefixes):
            return g
    return None


def probe_box(orig, opts):
    if opts.get("inpaint"):
        inset = 4
        return (inset, inset, orig.width - inset, orig.height - inset)
    pad = 2 if orig.width > 40 else 0
    return (pad, 0, orig.width - pad, orig.height)


def fit_size(text, bw, bh, stroke, cap=40):
    """Largest font size whose text fits the box height AND whose width
    fits after at most MIN_SQUEEZE horizontal condensation.  Grouped
    entries take the min of this over the group, so one size fits all."""
    d = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    size = min(bh + 4, cap)
    while size > 8:
        f = ImageFont.truetype(FONT, size)
        x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f, stroke_width=stroke)
        if y1 - y0 <= bh - 1 and (x1 - x0) * MIN_SQUEEZE <= bw:
            break
        size -= 1
    return size


def draw_fitted(im, text, box, fill, outline, stroke, size, ypos=None):
    """Draw text centered in box at the given font size.  Too-wide text is
    condensed horizontally (down to MIN_SQUEEZE); the font only shrinks
    further when even maximum condensation cannot fit the box."""
    bw, bh = box[2] - box[0], box[3] - box[1]
    d = ImageDraw.Draw(im)
    while True:
        f = ImageFont.truetype(FONT, size)
        x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f, stroke_width=stroke)
        tw, th = x1 - x0, y1 - y0
        if size <= 9 or (th <= bh and tw * MIN_SQUEEZE <= bw):
            break
        size -= 1
    cy = int(im.height * ypos) if ypos is not None else box[1] + bh // 2
    color = fill + (255,)
    oc = outline + (255,) if outline else None
    if tw <= bw:
        d.text((box[0] + (bw - tw) // 2 - x0, cy - th // 2 - y0),
               text, font=f, fill=color, stroke_width=stroke, stroke_fill=oc)
    else:
        tmp = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((-x0, -y0), text, font=f, fill=color,
                                 stroke_width=stroke, stroke_fill=oc)
        tmp = tmp.resize((max(1, bw), th), Image.LANCZOS)
        im.alpha_composite(tmp, (box[0], cy - th // 2))


def probe_size(orig, text, opts):
    """Font size this entry would pick on its own (height-fit only)."""
    if opts.get("inpaint") or "inpaint_x0" in opts:
        stroke = 1
    elif opts.get("fill") is not None:
        stroke = 1 if opts.get("outline") else 0
    else:
        stroke = 1 if sample_style(orig)[1] else 0
    box = probe_box(orig, opts)
    return fit_size(text, box[2] - box[0], box[3] - box[1], stroke)


def group_sizes(batch, cache, groups=GROUPS, probe=probe_size):
    """min height-fit size per group, so all members match."""
    sizes = {}
    for gld, idx, text, opts in batch:
        g = group_of(gld, groups, opts)
        if not g:
            continue
        pixels, palette, recs = cache[gld]
        orig = decode(pixels, palette, recs[idx])
        s = probe(orig, text, opts)
        sizes[g] = min(sizes.get(g, 99), s)
    return sizes


def load_batch(batch, cache):
    for gld, idx, text, opts in batch:
        if gld not in cache:
            data = open(os.path.join(SRC, gld + ".GLD"), "rb").read()
            cache[gld] = parse_gld(data)


def render(orig, text, opts, size=None):
    fill = opts.get("fill")
    outline = opts.get("outline")
    if fill is None:
        fill, outline = sample_style(orig)

    if opts.get("inpaint"):
        # text baked on an opaque button: keep original, repaint interior
        im = orig.copy()
        px = orig.load()
        colors = Counter(px[x, y][:3] for y in range(orig.height)
                         for x in range(orig.width) if px[x, y][3] >= 160)
        bg = colors.most_common(1)[0][0]
        inset = 4
        ImageDraw.Draw(im).rectangle(
            [inset, inset, orig.width - 1 - inset, orig.height - 1 - inset],
            fill=bg + (255,))
        fill = (255, 255, 255)
        outline = min(colors, key=lambda c: c[0] + c[1] + c[2])
    else:
        im = Image.new("RGBA", orig.size, (0, 0, 0, 0))

    stroke = 1 if outline else 0
    box = probe_box(orig, opts)
    if size is None:
        size = fit_size(text, box[2] - box[0], box[3] - box[1], stroke)
    draw_fitted(im, text, box, fill, outline, stroke, size)
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    cache = {}
    load_batch(BATCH, cache)
    sizes = group_sizes(BATCH, cache)
    for gld, idx, text, opts in BATCH:
        pixels, palette, recs = cache[gld]
        rec = recs[idx]
        orig = decode(pixels, palette, rec)
        im = render(orig, text, opts, size=sizes.get(group_of(gld, GROUPS,
                                                              opts)))
        name = f"{gld}_{idx:02d}_f{rec.fmt}.png"
        im.save(os.path.join(OUT, name))
        print(name, "<-", text)
    print(f"{len(BATCH)} images rendered into {OUT}")


if __name__ == "__main__":
    main()

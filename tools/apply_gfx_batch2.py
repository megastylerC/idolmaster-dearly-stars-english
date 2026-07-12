#!/usr/bin/env python3
"""Graphics translation batch 2: PDA management UI.

Same pattern as apply_gfx_batch1.py.  Extra option here:
  inpaint_x0=<frac>: repaint only the button interior right of frac*width
                     (keeps baked-in icons like the back arrow).
  erase_text=True:   remove text pixels by repainting them with the local
                     background (for text on shaped plates like mail tabs).

Run:  python -X utf8 tools/apply_gfx_batch2.py   (then tools/gld_import.py)
"""
import os
import sys
from collections import Counter

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from gld_export import parse_gld, decode
from apply_gfx_batch1 import (sample_style, fit_font, FONT, SRC, OUT,
                              group_of, group_sizes, load_batch,
                              fit_size, draw_fitted)

# images that appear together share one font size (see batch1 GROUPS note)
GROUPS = {
    "pda_header": ("PDA_MENU_TXT",),
    "pda_wnd": ("PDA_OVER_WND",),
    "pda_list": ("PDA_SELECT_TXT",),
    "pda_plate": ("PDA_SELECT_PLATE",),
    # plain text-crop buttons; the bordered inpaint buttons (Back/Send)
    # have less room and would drag the shared size down, so they group
    # separately per style
    "pda_btn": ("PDA_DATA_BTN", "PDA_SCHEDULE_BTN",
                "PDA_MAIL_BTN", "PDA_MAIL_UNREAD_BTN"),
    "pda_back": ("PDA_BACK_BTN",),
    "pda_send": ("PDA_TRANSMISSION_BTN",),
    "mail_hdr": ("PDA_MAILHEADER_",),
    "mail_cat": ("PDA_MAILCATEGORYO",),
    "mail_sub": ("PDA_MAIL_SUBWND",),
}

# (gld, rec index, text, options)
BATCH = [
    # ---- red screen headers (upper screen) ----
    ("PDA_MENU_TXT", 0, "MAIN MENU", {}),
    ("PDA_MENU_TXT", 1, "SELECT SCHEDULE", {}),
    ("PDA_MENU_TXT", 2, "SELECT LESSON", {}),
    ("PDA_MENU_TXT", 3, "PROMO LIST", {}),
    ("PDA_MENU_TXT", 4, "AUDITION LIST", {}),
    ("PDA_MENU_TXT", 5, "NEW CHOREOGRAPHY", {}),
    ("PDA_MENU_TXT", 6, "MAIL", {}),
    ("PDA_MENU_TXT", 7, "REST", {}),
    # ---- teal window headers ----
    ("PDA_OVER_WND", 0, "AUDITION", {"inpaint": True}),
    ("PDA_OVER_WND", 1, "LESSON", {"inpaint": True}),
    ("PDA_OVER_WND", 2, "MAIL", {"inpaint": True}),
    ("PDA_OVER_WND", 3, "MY MENU", {"inpaint": True}),
    ("PDA_OVER_WND", 4, "REST", {"inpaint": True}),
    ("PDA_OVER_WND", 5, "PROMO", {"inpaint": True}),
    ("PDA_OVER_WND", 6, "SCHEDULE", {"inpaint": True}),
    # ---- schedule pick list (pink) ----
    ("PDA_SELECT_TXT", 0, "Lesson", {}),
    ("PDA_SELECT_TXT", 1, "Promo", {}),
    ("PDA_SELECT_TXT", 2, "Audition", {}),
    ("PDA_SELECT_TXT", 3, "New choreography", {}),
    ("PDA_SELECT_TXT", 4, "Rest", {}),
    ("PDA_SELECT_TXT", 5, "Vocal Lesson", {}),
    ("PDA_SELECT_TXT", 6, "Dance Lesson", {}),
    ("PDA_SELECT_TXT", 7, "Visual Lesson", {}),
    ("PDA_SELECT_TXT", 8, "Promo 1", {}),
    ("PDA_SELECT_TXT", 9, "Promo 2", {}),
    ("PDA_SELECT_TXT", 10, "Promo 3", {}),
    ("PDA_SELECT_TXT", 11, "No promo work available now", {}),
    ("PDA_SELECT_TXT", 12, "Audition 1", {}),
    ("PDA_SELECT_TXT", 13, "Audition 2", {}),
    ("PDA_SELECT_TXT", 14, "Audition 3", {}),
    # ---- schedule plates (white / yellow / orange states) ----
    ("PDA_SELECT_PLATE", 9, "AUDITION", {}),
    ("PDA_SELECT_PLATE", 10, "AUDITION", {}),
    ("PDA_SELECT_PLATE", 11, "AUDITION", {}),
    ("PDA_SELECT_PLATE", 12, "LESSON", {}),
    ("PDA_SELECT_PLATE", 13, "LESSON", {}),
    ("PDA_SELECT_PLATE", 14, "LESSON", {}),
    ("PDA_SELECT_PLATE", 15, "REST", {}),
    ("PDA_SELECT_PLATE", 16, "REST", {}),
    ("PDA_SELECT_PLATE", 17, "REST", {}),
    ("PDA_SELECT_PLATE", 18, "PROMO", {}),
    ("PDA_SELECT_PLATE", 19, "PROMO", {}),
    ("PDA_SELECT_PLATE", 20, "PROMO", {}),
    # ---- buttons ----
    ("PDA_BACK_BTN", 0, "Back", {"inpaint_x0": 0.30}),
    ("PDA_BACK_BTN", 1, "Back", {"inpaint_x0": 0.30}),
    ("PDA_BACK_BTN", 2, "Back", {"inpaint_x0": 0.30}),
    ("PDA_DATA_BTN", 4, "Save", {}),
    ("PDA_DATA_BTN", 5, "Save", {}),
    ("PDA_DATA_BTN", 6, "Save", {}),
    ("PDA_DATA_BTN", 7, "Save", {}),
    ("PDA_DATA_BTN", 8, "Save", {}),
    ("PDA_SCHEDULE_BTN", 0, "Schedule", {}),
    ("PDA_SCHEDULE_BTN", 1, "Schedule", {}),
    ("PDA_SCHEDULE_BTN", 2, "Schedule", {}),
    ("PDA_SCHEDULE_BTN", 3, "Schedule", {}),
    ("PDA_SCHEDULE_BTN", 4, "Schedule", {}),
    ("PDA_SCHEDULE_BTN", 5, "Schedule", {}),
    ("PDA_SCHEDULE_BTN", 6, "Schedule", {}),
    ("PDA_SCHEDULE_BTN", 7, "Schedule", {}),
    ("PDA_MAIL_BTN", 0, "Mail", {}),
    ("PDA_MAIL_BTN", 2, "Mail", {}),
    ("PDA_MAIL_BTN", 4, "Mail", {}),
    ("PDA_MAIL_BTN", 6, "Mail", {}),
    ("PDA_MAIL_BTN", 8, "Mail", {}),
    ("PDA_MAIL_UNREAD_BTN", 0, "Mail", {}),
    ("PDA_MAIL_UNREAD_BTN", 2, "Mail", {}),
    ("PDA_MAIL_UNREAD_BTN", 4, "Mail", {}),
    ("PDA_MAIL_UNREAD_BTN", 6, "Mail", {}),
    ("PDA_MAIL_UNREAD_BTN", 8, "Mail", {}),
    ("PDA_TRANSMISSION_BTN", 0, "Send", {"inpaint": True}),
    ("PDA_TRANSMISSION_BTN", 1, "Send", {"inpaint": True}),
    ("PDA_TRANSMISSION_BTN", 2, "Send", {"inpaint": True}),
    # ---- mail screen labels ----
    ("PDA_MAILHEADER_M_BTN", 0, "Unread", {"inpaint": True, "inset": 2}),
    ("PDA_MAILHEADER_M_BTN", 1, "Unread", {"inpaint": True, "inset": 2}),
    ("PDA_MAILHEADER_N_BTN", 0, "New", {"inpaint": True, "inset": 2}),
    ("PDA_MAILHEADER_N_BTN", 1, "New", {"inpaint": True, "inset": 2}),
    ("PDA_MAILHEADER_S_BTN", 0, "Sender", {"inpaint": True, "inset": 2}),
    ("PDA_MAILHEADER_S_BTN", 1, "Sender", {"inpaint": True, "inset": 2}),
    ("PDA_MAILCATEGORYO_G_TXT", 0, "All", {}),
    ("PDA_MAILCATEGORYO_M_TXT", 0, "New", {}),
    ("PDA_MAIL_SUBWND", 0, "Sending", {}),
    ("PDA_MAIL_SUBWND", 1, "Sent!", {}),
]


def dominant(colors):
    return colors.most_common(1)[0][0]


def probe_box(orig, opts):
    if opts.get("inpaint") or "inpaint_x0" in opts:
        inset = opts.get("inset", 4)
        x0 = int(orig.width * opts.get("inpaint_x0", 0)) or inset
        return (x0, inset, orig.width - inset, orig.height - inset)
    pad = 2 if orig.width > 40 else 0
    return (pad, 0, orig.width - pad, orig.height)


def probe_size(orig, text, opts):
    if opts.get("inpaint") or "inpaint_x0" in opts or opts.get("erase_text"):
        stroke = 1
    else:
        stroke = 1 if sample_style(orig)[1] else 0
    box = probe_box(orig, opts)
    return fit_size(text, box[2] - box[0], box[3] - box[1], stroke)


def render(orig, text, opts, size=None):
    im = Image.new("RGBA", orig.size, (0, 0, 0, 0))
    fill, outline = sample_style(orig)

    if opts.get("inpaint") or "inpaint_x0" in opts:
        im = orig.copy()
        px = orig.load()
        colors = Counter(px[x, y][:3] for y in range(orig.height)
                         for x in range(orig.width) if px[x, y][3] >= 160)
        bg = dominant(colors)
        inset = opts.get("inset", 4)
        x0 = int(orig.width * opts.get("inpaint_x0", 0)) or inset
        d = ImageDraw.Draw(im)
        d.rectangle([x0, inset, orig.width - 1 - inset,
                     orig.height - 1 - inset], fill=bg + (255,))
        fill = (255, 255, 255)
        outline = min(colors, key=lambda c: sum(c[:3]))
    elif opts.get("erase_text"):
        # repaint text-colored pixels with the plate background color
        im = orig.copy()
        px = im.load()
        colors = Counter(px[x, y][:3] for y in range(orig.height)
                         for x in range(orig.width) if px[x, y][3] >= 160)
        bg = dominant(colors)

        def is_textish(c):
            r, g, b = c
            lum = (r + g + b) / 3
            return lum > 200 or lum < 110  # white glyphs + dark outline

        for y in range(im.height):
            for x in range(im.width):
                r, g, b, a = px[x, y]
                if a >= 100 and is_textish((r, g, b)):
                    px[x, y] = bg + (a,)
        fill = (255, 255, 255)
        outline = min(colors, key=lambda c: sum(c[:3]))

    stroke = 1 if outline else 0
    box = probe_box(orig, opts)
    if size is None:
        size = fit_size(text, box[2] - box[0], box[3] - box[1], stroke)
    draw_fitted(im, text, box, fill, outline, stroke, size,
                ypos=opts.get("ypos"))
    return im


def render_tabs():
    """Mail folder tabs: two-zone repaint (kanji on white top half, white
    text on pink banner bottom), then one English word across the middle."""
    for gldname, text in (("PDA_MAILHEADER_P_TAB", "Saved"),
                          ("PDA_MAILHEADER_R_TAB", "Inbox")):
        data = open(os.path.join(SRC, gldname + ".GLD"), "rb").read()
        pixels, palette, recs = parse_gld(data)
        for idx in (0, 1):
            orig = decode(pixels, palette, recs[idx])
            im = orig.copy()
            px = im.load()
            W, H = im.size
            halves = [Counter(), Counter()]
            for y in range(H):
                for x in range(W):
                    c = px[x, y]
                    if c[3] >= 160:
                        halves[y * 2 // H][(c[0] // 8 * 8, c[1] // 8 * 8,
                                            c[2] // 8 * 8)] += 1
            bg = [h.most_common(1)[0][0] if h else (255, 255, 255)
                  for h in halves]

            def near_edge(x, y):
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        nx, ny = x + dx, y + dy
                        if not (0 <= nx < W and 0 <= ny < H)                                 or px[nx, ny][3] < 64:
                            return True
                return False

            for y in range(H):
                b = bg[y * 2 // H]
                for x in range(W):
                    r, g, bl, a = px[x, y]
                    if a < 100:
                        continue
                    if (r - b[0]) ** 2 + (g - b[1]) ** 2 + (bl - b[2]) ** 2                             > 3600 and not near_edge(x, y):
                        px[x, y] = b + (a,)
            d = ImageDraw.Draw(im)
            f, (x0, y0, x1, y1) = fit_font(d, text, W - 6, H // 2, 1)
            d.text(((W - (x1 - x0)) // 2 - x0,
                    int(H * 0.52 - (y1 - y0) / 2) - y0), text, font=f,
                   fill=(226, 66, 132, 255), stroke_width=1,
                   stroke_fill=(255, 255, 255, 255))
            im.save(os.path.join(
                OUT, f"{gldname}_{idx:02d}_f{recs[idx].fmt}.png"))
            print(gldname, idx, "(custom tab)")


def main():
    os.makedirs(OUT, exist_ok=True)
    cache = {}
    load_batch(BATCH, cache)
    sizes = group_sizes(BATCH, cache, groups=GROUPS, probe=probe_size)
    for gld, idx, text, opts in BATCH:
        pixels, palette, recs = cache[gld]
        rec = recs[idx]
        orig = decode(pixels, palette, rec)
        im = render(orig, text, opts, size=sizes.get(group_of(gld, GROUPS,
                                                              opts)))
        name = f"{gld}_{idx:02d}_f{rec.fmt}.png"
        im.save(os.path.join(OUT, name))
        print(name, "<-", text)
    render_tabs()
    print(f"{len(BATCH) + 4} images rendered into {OUT}")


if __name__ == "__main__":
    main()

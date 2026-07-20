# -*- coding: utf-8 -*-
"""BLZ ("bottom LZ") compressor - the missing half of blz.py.

Encodes backward, mirroring blz.decompress: the stream is decoded from high
addresses to low, so we emit tokens the same way and reverse at the end.
Token: literal, or (disp 3..4098, len 3..18) referencing bytes at HIGHER
addresses (already decoded).  Tokens are grouped in 8s behind a flag byte that
sits at the highest address of its group.

Two properties this module exists to preserve, both required for the ARM9 to
stay at ROM 0x4000 where real hardware expects it:

  * The raw prefix (data[:split]) is stored verbatim.  For arm9.bin split is
    0x4000, and that prefix IS the cart secure area - so it never changes.
  * `pad_to` lets the caller hit an exact output size.  Padding goes at the
    BOTTOM of the compressed region, which the decoder never reads (it stops
    as soon as out_pos hits 0), so the ARM9 can be recompressed to the exact
    original length and leave ModuleParams / the secure-area CRC untouched.

Because the patched image differs from the original in only a few small
regions, `recompress_tail` re-encodes just the changed tail and splices the
original stream underneath it, which is both fast and size-competitive with
Nintendo's own encoder.
"""
import struct
from bisect import bisect_left, bisect_right

MIN_MATCH = 3
MAX_MATCH = 18
MIN_DISP = 3
MAX_DISP = 4098


def decompress_strict(data):
    """Decompress exactly the way the game's CRT0 does, for verification.

    Critically, the real decompressor terminates when the SOURCE pointer
    reaches the end of the raw prefix - NOT when the destination is full, which
    is what blz.py checks.  Any byte inside the compressed region gets decoded
    as a token whether or not the output is already complete, so a stream that
    round-trips under blz.py can still corrupt RAM on hardware.  Returns
    (decompressed, dst_landing); dst_landing must equal the raw prefix length.
    """
    fs = len(data)
    ci, extra = struct.unpack_from("<II", data, fs - 8)
    hdr, cl = ci >> 24, ci & 0xFFFFFF
    raw_end = fs - cl
    src, dst = fs - hdr, fs + extra
    buf = bytearray(data) + bytearray(extra)
    while src > raw_end:
        src -= 1
        flags = buf[src]
        for bit in range(8):
            if src <= raw_end:
                break
            if flags & (0x80 >> bit):
                src -= 2
                info = (buf[src + 1] << 8) | buf[src]
                ln, disp = (info >> 12) + 3, (info & 0xFFF) + 3
                for _ in range(ln):
                    dst -= 1
                    buf[dst] = buf[dst + disp]
            else:
                src -= 1
                dst -= 1
                buf[dst] = buf[src]
    return bytes(buf), dst


def parse_groups(data, split, src):
    """Walk `src` like the decoder does, recording every flag-group boundary.

    Returns [(abs_pos, src_pos), ...] where abs_pos is the absolute offset in
    the decompressed image that the decoder is about to fill when it reads the
    flag byte at src_pos.  Splicing is only legal at one of these points.
    """
    out_len = len(data) - split
    out_pos = out_len
    src_pos = len(src)
    marks = []
    while out_pos > 0 and src_pos > 0:
        marks.append((split + out_pos, src_pos))
        src_pos -= 1
        flags = src[src_pos]
        for bit in range(8):
            if out_pos <= 0 or src_pos <= 0:
                break
            if flags & (0x80 >> bit):
                src_pos -= 2
                info = (src[src_pos + 1] << 8) | src[src_pos]
                out_pos -= (info >> 12) + 3
            else:
                src_pos -= 1
                out_pos -= 1
    return marks


def _build_index(data, lo, hi):
    """3-byte-suffix index: key (d[q-2],d[q-1],d[q]) -> ascending end offsets q."""
    idx = {}
    for q in range(lo + 2, hi):
        idx.setdefault(data[q - 2:q + 1], []).append(q)
    return idx


def _longest_match(data, c, index, lo_bound):
    """Longest match at cursor c: covers data[c-L:c], sourced from c-L+disp.
    Returns (length, disp), or (0, 0).  Any L' < L with the same disp is also
    valid, which is what lets the DP treat lengths 3..L uniformly.
    """
    if c - MIN_MATCH < lo_bound:
        return 0, 0
    cand = index.get(data[c - 3:c])
    if not cand:
        return 0, 0
    anchor = c - 1
    lo_q = anchor + MIN_DISP
    hi_q = min(anchor + MAX_DISP, len(data) - 1)
    best_len, best_disp = 0, 0
    for q in cand[bisect_left(cand, lo_q):bisect_right(cand, hi_q)]:
        L = 0
        while (L < MAX_MATCH and anchor - L >= lo_bound
               and data[anchor - L] == data[q - L]):
            L += 1
        if L > best_len:
            best_len, best_disp = L, q - anchor
            if L == MAX_MATCH:
                break
    return (best_len, best_disp) if best_len >= MIN_MATCH else (0, 0)


# cost in 1/8-byte units: a token's body plus its one flag bit
LIT_COST = 8 * 1 + 1
MATCH_COST = 8 * 2 + 1


def encode_backward(data, top, stop_at, index, lo_bound):
    """Optimally encode data[stop:top] downward for some stop in `stop_at`.

    Dynamic program over (cursor, token_count mod 8).  The mod-8 dimension is
    required: we may only stop on a completed flag group, otherwise the spliced
    original stream's flag bytes would be misaligned.  Returns (bytes, stop).
    """
    INF = float("inf")
    span = top - lo_bound + 1
    # dist[c - lo_bound][phase] -> cost in 1/8-byte units
    dist = [[INF] * 8 for _ in range(span)]
    back = [[None] * 8 for _ in range(span)]
    dist[top - lo_bound][0] = 0

    matches = {}
    for c in range(top, lo_bound, -1):
        i = c - lo_bound
        row = dist[i]
        if min(row) == INF:
            continue
        L, disp = _longest_match(data, c, index, lo_bound)
        if L:
            matches[c] = (L, disp)
        for ph in range(8):
            base = row[ph]
            if base == INF:
                continue
            nph = (ph + 1) & 7
            # literal
            j = i - 1
            if j >= 0 and base + LIT_COST < dist[j][nph]:
                dist[j][nph] = base + LIT_COST
                back[j][nph] = (c, ph, 0, 0)
            # matches of every valid length
            for ln in range(MIN_MATCH, L + 1):
                j = i - ln
                if j < 0:
                    break
                if base + MATCH_COST < dist[j][nph]:
                    dist[j][nph] = base + MATCH_COST
                    back[j][nph] = (c, ph, ln, disp)

    best, best_stop = INF, None
    for s in stop_at:
        if lo_bound <= s <= top and dist[s - lo_bound][0] < best:
            best, best_stop = dist[s - lo_bound][0], s
    if best_stop is None:
        raise RuntimeError("no reachable aligned splice point")

    # walk back up, recovering tokens in emission order (high -> low)
    toks = []
    c, ph = best_stop, 0
    while (c, ph) != (top, 0):
        pc, pph, ln, disp = back[c - lo_bound][ph]
        toks.append((ln, disp) if ln else (0, data[pc - 1]))
        c, ph = pc, pph
    toks.reverse()

    emitted = []
    for g in range(0, len(toks), 8):
        group = toks[g:g + 8]
        flag = 0
        body = []
        for bit, (ln, x) in enumerate(group):
            if ln:
                flag |= 0x80 >> bit
                info = ((ln - 3) << 12) | (x - 3)
                body.append((info >> 8) & 0xFF)
                body.append(info & 0xFF)
            else:
                body.append(x)
        emitted.append(flag)
        emitted.extend(body)
    return bytes(reversed(emitted)), best_stop


def recompress_tail(dec, orig_comp, split, first_change, pad_to=None,
                    header_len=9, search_margin=0x4000):
    """Rebuild a BLZ image whose decompressed form is `dec`.

    Re-encodes only the tail at/above `first_change` and reuses `orig_comp`'s
    stream below it.  `pad_to`, if given, is the exact total file size to emit.
    """
    ci, _ = struct.unpack_from("<II", orig_comp, len(orig_comp) - 8)
    o_hdr, o_comp = ci >> 24, ci & 0xFFFFFF
    assert len(orig_comp) - o_comp == split, "split must match the original prefix"
    src = orig_comp[len(orig_comp) - o_comp:len(orig_comp) - o_hdr]

    marks = parse_groups(dec, split, src)
    # Candidate splice points.  A reused original token at cursor c references
    # bytes as high as c - 1 + MAX_DISP, so splicing merely "below the first
    # change" is not enough - tokens under the splice would still resolve
    # against string bytes we rewrote.  The splice must clear the whole match
    # window, or the reused stream decodes to stale data.
    ceiling = first_change - MAX_DISP - MAX_MATCH
    cands = {pos: sp for pos, sp in marks
             if pos <= ceiling and pos >= ceiling - search_margin}
    assert cands, "no original group boundary below the match window"

    lo_bound = min(cands)
    index = _build_index(dec, lo_bound, len(dec))

    stream, stop = encode_backward(dec, len(dec), set(cands), index, lo_bound)

    # Coarse size control: raise the raw-prefix boundary.  Dropping whole flag
    # groups off the BOTTOM of the reused stream and storing that data verbatim
    # instead grows the image by roughly 0.4 bytes per byte moved, and yields a
    # completely ordinary BLZ image.  This is how we spend the surplus when our
    # encoder beats the original by more than header_len can absorb.
    #
    # Fine control is the padding between the stream and the footer, absorbed
    # into header_len - the one region the decoder provably never reads, since
    # it starts at (end - header_len).  Padding at the BOTTOM of the compressed
    # region would instead be decoded as tokens and write below the intended
    # start, corrupting RAM (not hypothetical: it white-screened).
    prefix_end, src_start = split, 0
    if pad_to is not None:
        best = None
        for pos, sp in marks:
            if pos > stop or sp > cands[stop]:
                continue
            n = pos + (cands[stop] - sp) + len(stream) + 8
            if n <= pad_to and (best is None or n > best[0]):
                best = (n, pos, sp)
        assert best is not None, "cannot reach target size"
        _, prefix_end, src_start = best

    new_src = src[src_start:cands[stop]] + stream
    natural = prefix_end + len(new_src) + 8
    if pad_to is None:
        pad_to = natural
    pad = pad_to - natural
    assert pad >= 0, f"cannot fit: need {natural}, target {pad_to}"
    header_len = 8 + pad
    assert header_len <= 0xFF, f"header_len {header_len} exceeds the byte field"

    comp_len = len(new_src) + header_len
    out = bytearray(dec[:prefix_end]) + new_src + b"\xFF" * pad
    out += struct.pack("<II", (header_len << 24) | comp_len, len(dec) - pad_to)
    assert len(out) == pad_to
    out = bytes(out)

    # Self-check against BOTH decoders. The strict one models the real CRT0 and
    # is the one that actually matters; blz.py is kept as a cross-check.
    import blz
    got, dst = decompress_strict(out)
    assert dst == prefix_end, f"strict decode landed at {dst:#x}, expected {prefix_end:#x}"
    assert got == dec, "strict BLZ round-trip mismatch"
    assert blz.is_blz(out) and blz.decompress(out) == dec, "blz.py round-trip mismatch"
    return out

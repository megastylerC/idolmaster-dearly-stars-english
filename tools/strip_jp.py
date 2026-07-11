# -*- coding: utf-8 -*-
"""Produce an English-only copy of translation/ for publishing.

The working translation JSONs carry the original Japanese ('jp') next to
each English line as a reference. That Japanese is the game's copyrighted
script, so it must NOT be committed to the public repo. This copies every
translation JSON with the 'jp' fields removed; contributors regenerate the
Japanese locally from their own ROM (see tools/show_jp.py).

The build/verify pipeline never needs 'jp' (the archive build keys off
line index + 'en'; the overlay/arm9 build derives patch length from each
string's own NUL terminator), so the stripped copy builds identically.

Usage: python tools/strip_jp.py [SRC_ROOT] [DST_ROOT]
  defaults: SRC_ROOT=translation  DST_ROOT=github-repo/translation
"""
import glob
import json
import os
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "translation"
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join("github-repo", "translation")


def strip_line(line, keep):
    """Keep only the given keys (drop 'jp')."""
    return {k: line[k] for k in keep if k in line}


def convert(doc):
    if "lines" in doc:  # archive file: {file, count, lines:[{i, jp, en}]}
        return {
            "file": doc["file"],
            "count": doc["count"],
            "lines": [strip_line(l, ("i", "en")) for l in doc["lines"]],
        }
    if "strings" in doc:  # overlay/arm9: {[overlay,] strings:[{off, jp, en}]}
        out = {k: doc[k] for k in doc if k != "strings"}
        out["strings"] = [strip_line(s, ("off", "en")) for s in doc["strings"]]
        return out
    raise ValueError(f"unrecognized JSON shape: keys={list(doc)}")


count = 0
for src_path in glob.glob(os.path.join(SRC, "**", "*.json"), recursive=True):
    rel = os.path.relpath(src_path, SRC)
    dst_path = os.path.join(DST, rel)
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    doc = json.load(open(src_path, encoding="utf-8"))
    json.dump(convert(doc), open(dst_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    count += 1

print(f"stripped {count} file(s): {SRC} -> {DST}")

# -*- coding: utf-8 -*-
"""Show the Japanese source text next to the current English, for
translating. Reads the Japanese live from your locally-unpacked ROM data
(unpacked/), so no copyrighted text needs to live in the repo.

Prerequisites (one-time, from your own Japanese ROM):
    python tools/nds_extract.py <your_rom.nds>    # -> extracted/
    python tools/ez_extract.py                     # -> unpacked/

Usage:
    python -X utf8 tools/show_jp.py F_SCN/ERI_E03_MAIN01_MES.BBQ
    python -X utf8 tools/show_jp.py F_SCN/ERI_E03_MAIN01_MES.BBQ --todo

Options:
    --todo   only print lines whose English is still empty

Prints one line per string:  <index> \\t <japanese> \\t <english>
Use the index to fill in the matching "en" in
translation/<ARC>/<file>.json (or write an apply_*.py script - see
tools/apply_eri_e03b.py for the pattern). Keep one English entry per
index; if a line needs to wrap, put a \\n inside the single string
rather than shifting to the next index (that silently misaligns
everything after it).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from bbq_text import extract_strings

if len(sys.argv) < 2:
    sys.exit(__doc__)

member = sys.argv[1].replace("\\", "/")           # e.g. F_SCN/FILE.BBQ
todo_only = "--todo" in sys.argv[2:]

blob = open(os.path.join("unpacked", *member.split("/")), "rb").read()
res = extract_strings(blob)
if res is None:
    sys.exit(f"no string pool in {member}")
_, strs = res

json_path = os.path.join("translation", *member.split("/")) + ".json"
en_by_i = {}
if os.path.exists(json_path):
    doc = json.load(open(json_path, encoding="utf-8"))
    en_by_i = {l["i"]: (l.get("en") or "") for l in doc["lines"]}

shown = 0
for i, jp in enumerate(strs):
    if not jp:
        continue
    en = en_by_i.get(i, "")
    if todo_only and en:
        continue
    print(f"{i}\t{jp}\t{en}")
    shown += 1

done = sum(1 for v in en_by_i.values() if v)
print(f"\n# {member}: {done}/{len(en_by_i)} translated, {shown} line(s) shown",
      file=sys.stderr)

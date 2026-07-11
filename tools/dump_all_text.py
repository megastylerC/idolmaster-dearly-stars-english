"""Dump string pools of every BBQ file into translation JSON files.

Output: translation/<archive>/<file>.json
  {"file": ..., "count": N, "lines": [{"i": 0, "jp": "...", "en": null}, ...]}
Skips files with no string pool or with no Japanese text at all.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from bbq_text import extract_strings


def has_jp(s):
    return any("぀" <= c <= "ヿ" or "一" <= c <= "鿿" or c in "、。！？…♪" for c in s)


total_files = 0
total_lines = 0
total_chars = 0
skipped = []
for arc in ("F_SCN", "F_TBL"):
    src = os.path.join("unpacked", arc)
    dst = os.path.join("translation", arc)
    os.makedirs(dst, exist_ok=True)
    for fn in sorted(os.listdir(src)):
        if not fn.upper().endswith((".BBQ", ".CHE")):
            continue
        path = os.path.join(src, fn)
        d = open(path, "rb").read()
        if len(d) < 0x60 or d[:4] != b".BBQ":
            skipped.append((arc, fn, "not BBQ"))
            continue
        try:
            res = extract_strings(d)
        except Exception as e:
            skipped.append((arc, fn, f"error {e}"))
            continue
        if res is None:
            skipped.append((arc, fn, "no pool"))
            continue
        _, strs = res
        jp_lines = [s for s in strs if has_jp(s)]
        if not jp_lines:
            continue
        doc = {
            "file": f"{arc}/{fn}",
            "count": len(strs),
            "lines": [{"i": i, "jp": s, "en": None} for i, s in enumerate(strs) if s],
        }
        with open(os.path.join(dst, fn + ".json"), "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        total_files += 1
        total_lines += len(doc["lines"])
        total_chars += sum(len(s) for s in strs)

print(f"dumped {total_files} files, {total_lines} strings, {total_chars} JP chars")
print(f"skipped: {len(skipped)}")
from collections import Counter
print(Counter(r for _, _, r in skipped).most_common(5))

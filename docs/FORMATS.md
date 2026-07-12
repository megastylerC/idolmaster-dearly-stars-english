# File formats

Reverse-engineered notes on how Dearly Stars stores its data, and how the pipeline patches it. This is background for tool hackers; translators don't need it.

All multi-byte integers are little-endian. Text is Shift-JIS (cp932).

## ROM layout

Standard Nintendo DS layout. The build only touches a few header fields:

| Offset | Meaning |
|---|---|
| `0x20` / `0x2C` | ARM9 ROM offset / size |
| `0x28` | ARM9 RAM address |
| `0x40` | FNT (filename table) offset |
| `0x48` / `0x4C` | FAT offset / size |
| `0x50` / `0x54` | overlay table offset / size |
| `0x80` | used ROM size |
| `0x90` / `0x92` | NTR (DS-mode) region size, in `0x80000`-byte units (u16 each) |
| `0x15E` | header CRC16 |

This is a **DSi-enhanced** cartridge. On DSi carts, accurate emulators (melonDS) and hardware block DS-mode reads past the region boundary at `0x90`/`0x92`. Because the build relocates patched data into the end-of-ROM padding, it must **extend** that boundary (and `0x80`) to cover the new data, or the game freezes at the first read past the old limit. DeSmuME doesn't emulate the block, which hides the bug — so always test relocations on melonDS.

The DSi security hashes are **not** fixed, so the patched ROM only boots in **NDS mode**.

## EZ archives (`EZT`/`EZP`)

Data files come as `F_*.IDX` + `F_*.BIN` pairs.

**IDX** — 16-byte header (`EZT\0`, date, entry count), then 12-byte entries:
```
offset      u32   into BIN
szflags     u32   flags<<24 | uncompressedSize
nameOffset  u32   into the BIN name table
```
The last entry is a terminator (its `offset` = end of data). Flag `0x10` = the member is NDS LZ77-compressed (type `0x10`); flags+size both 0 = empty file.

**BIN** — 16-byte header (`EZP\0`, date, dataEnd u32), then the member blobs, then a NUL-padded Shift-JIS filename table starting at `dataEnd`.

`tools/ez_extract.py` unpacks these into `unpacked/<ARC>/`; `tools/lz77.py` does the LZ77 (de)compression.

## BBQ scripts

Members are `.BBQ1.00` bytecode files (`.BBQ` magic). Story dialogue is in `F_SCN/*_MES.BBQ` (one per scene); the matching file **without** `_MES` holds that scene's choice-button strings. Tables live in `F_TBL`.

Each BBQ has a **string pool**: near the end, a tail record `7, tblOff, count, poolOff, poolSize` (offsets relative to the position of the `7` marker) points at an offset table of `count` u32s immediately preceding a pool of NUL-terminated cp932 strings. `tools/bbq_text.py` (`find_pool`, `extract_strings`) locates and reads it; `tools/bbq_patch.py` rewrites it.

When patching, the offset table must stay **monotonic** — do not dedupe identical strings. The wide-dash glyph `―㌍` (bytes `0x815C 0x875E`) must be preserved verbatim.

Fonts `LC10.NFTR`/`LC12.NFTR` (in `F_TBL`) include the full ASCII range `U+0020`–`U+007E`, so English renders natively. Japanese lines wrap at ~19 fullwidth characters; keep English lines within ~38 halfwidth.

## BLZ-compressed binaries (ARM9 + overlays)

The ARM9 binary, its overlays, and the download-play inner ARM9s are **BLZ**-compressed (a backwards LZ variant; `tools/blz.py` — `is_blz`, `decompress`; the info-byte pair is read little-endian walking backward, high byte at the higher address). System-UI text lives in these.

There is no BLZ **compressor** in this project and none is needed — patched binaries are stored **decompressed** and the loader is told to copy them as-is:

- **Overlays.** Patch the target strings in place in the decompressed image (English must fit within the original NUL-terminated run — the build derives that length from the run's own terminator). Store the overlay decompressed in the end padding, retarget its FAT entry (the file id in the overlay-table entry), and clear the "compressed" flag (bit 0) in the overlay-table entry so the loader copies it verbatim.
- **ARM9.** Same idea, plus: zero the `ModuleParams` compressed-size pointer (the u32 eight bytes before the nitrocode magic `21 06 C0 DE DE C0 06 21`) so CRT0 skips in-place decompression, store the ARM9 decompressed in the padding, and retarget header `0x20` (ROM offset) and `0x2C` (size). Entry point and RAM address are unchanged. Relocating past `0x8000` means emulators apply no secure-area processing — the bytes are copied verbatim.

In every case the English bytes must be **≤** the original run's byte length; shorter strings are NUL-padded. Patch a whole NUL-terminated run or the **tail** of one — never a prefix (an early NUL would truncate the rest of the run).

## The pipeline

| Tool | Role |
|---|---|
| `nds_extract.py` | ROM → `extracted/` (filesystem + `_system/` ARM9/overlays) |
| `ez_extract.py` | archives → `unpacked/<ARC>/` |
| `dump_all_text.py` | BBQ string pools → `translation/<ARC>/*.json` (maintainer bootstrap) |
| `show_jp.py` | show Japanese (from your ROM) next to current English |
| `bbq_patch.py` | rewrite a BBQ string pool with English |
| `lz77.py` / `blz.py` | (de)compression |
| `build_rom.py` | patch everything, relocate, fix FAT + header → new `.nds` |
| `verify_rom.py` | round-trip every translated string out of the built ROM |
| `strip_jp.py` | produce the English-only `translation/` copy for publishing |

`build_rom.py` keys archive strings off line **index + English** and derives overlay/ARM9 patch lengths from each string's own NUL terminator, so it never needs the Japanese — the English-only data in this repo builds a byte-identical ROM to the maintainer's full working copy.

## GLD texture files (`F_AGL`) — UI graphics

Menu buttons, screen headers, and minigame tiles are images, not text. They live in `.GLD` files (magic `\0DLG`) inside the `F_AGL` archive, usually with an `.AGL` companion (layout/animation records — never touched; image dimensions must stay the same).

GLD layout: `0x20` header (`+0x08` fileSize, `+0x0c` pixelDataSize, `+0x18` paletteBlockSize, `+0x1c` imageCount), then pixel data (offsets are 0x20-based), a BGR555 palette block, and `imageCount` records of 28 bytes (version pair (2,2)) or 24 bytes (older (2,1)): `u32 pixOff, u16 palOffBytes, u16 fmt, u16 w, u16 h, u16 S, u16 T, u16 xoff, u16 yoff` (crop offsets, 28-byte records only). `fmt` is the NDS texture format (1=A3I5, 2=I2, 3=I4, 4=I8, 6=A5I3, 7=direct16; index 0 = transparent). `fmt|0x8000` means no pixel data (flat fill rect). Records are **crops in a strided block** — row stride is `8<<S` **pixels**, and several records can share one block side by side, or alias the same pixels with different palettes (recolor variants).

Workflow: `gld_export.py --all` dumps every image to `gfx/F_AGL/*.png`; the `apply_gfx_*.py` scripts render English replacements into `gfx/edited/F_AGL/` (same size as the original, style colors sampled from it, one shared font size per group of images that appear together); `gld_import.py` quantizes each PNG back to its record's original palette and writes `patched/F_AGL/*.GLD`, which `build_rom.py` picks up when rebuilding the archive.

Two non-obvious wins from this: the save/status-screen **kanji name plates** are split across records drawn flush (`水谷絵|理`), so English names are rendered across a combined canvas and sliced back; and the **vocal-lesson minigame** (which looks glyphs up by kana code, so its *text* can never be ASCII) became playable by redrawing all 81 kana tiles as romaji.

## Scale

~71,000 strings / ~856K Japanese characters across ~1,170 files. The ARM9 itself has very little text; most core UI **graphics** (labels drawn into images in `F_AGL` GLD files) are redrawn in English as of v0.3; stage-editor/wireless/logo art remains.

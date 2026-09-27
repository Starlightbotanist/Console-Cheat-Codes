# Gran Turismo 2 NTSC-U 1.2: RetroArch 16:9 widescreen

This folder has one disabled RetroArch cheat entry for the **original NTSC-U
1.2 game revision**. It applies the 37 guarded writes in the neighboring
[`NTSC-U 1.2.cht`](../NTSC-U%201.2.cht) through Beetle PSX/PSX HW,
PCSX-ReARMed, or SwanStation. The source file and its original comments are
unchanged. The [per-write map](ANNOTATED.md) shows every source write and the
instructions intended for each core.

**Beetle requirement:** Beetle must include streaming cheat-code parsing. The
currently released parser stores only 64 hex tokens and truncates this entry;
that can apply only part of the patch. The file is therefore a review/test
candidate until the Beetle parser change is available in ordinary core builds.
PCSX-ReARMed and SwanStation need no core changes.

## Use and test status

Load `NTSC-U 1.2 - Universal.cht` in RetroArch's Cheats menu, enable its one
entry, choose **Apply Changes**, and set the display aspect ratio to 16:9. To
return to 4:3, disable the entry, apply changes, and restart or reload the
game. Disabling does not undo values already written to RAM.

On the Odin 2, the user reported correct visuals with this exact code string
in Beetle PSX HW (debug RetroArch with the streaming parser), SwanStation
(regular RetroArch), and PCSX-ReARMed (regular RetroArch). Other game revisions
have separately generated candidates but have not received these live tests.
This file has no revision detector; select it only for NTSC-U 1.2.

## Why the code is long

RetroArch sends an emulator-handled cheat string to the selected core. The
three cores parse the same string differently, so each source write appears
in three forms. The original `A4` checks a 32-bit game-code signature. `A7`
replaces a 16-bit value only if its original value remains there. Four `80`
writes clear overlay markers under an `A4` guard.

| Core | Equivalent action for one guarded write |
| --- | --- |
| Beetle | Two `D0` tests check both halves of `A4`; an additional `D0` checks an `A7` target, then `80` writes. Beetle stacks the tests. |
| PCSX-ReARMed | `D0` and `D1` tests plus a zero-length `C2` copy control the final `80`. A failed test skips **one** following instruction, so a plain Beetle `D0` stack would be wrong here. |
| SwanStation | The original `A4`/`A7` block expresses compare-and-replace directly. A zero-width `F1` clears an overlay marker. |

The three streams coexist through parser-specific syntax:

1. A Beetle instruction is written `0+ADDRESS+VALUE+0`. Beetle joins the
   eight- and four-digit fields. ReARMed treats the resulting low-address
   lines as ignored codes; SwanStation sees no-op `00` instructions.
2. A SwanStation instruction is written `0xADDRESS+0xVALUE`. SwanStation
   accepts the `0x` prefixes. ReARMed splits at each `x` and ignores the
   low-address lines. Beetle's hex-token scanner does not assemble a
   GameShark instruction from those fields.
3. ReARMed's `D0`/`D1`/`C2`/`80` sequence remains visible to Beetle, so a
   Beetle-only impossible `D2 000000 0000` condition prevents its dummy
   copy patch from writing. SwanStation instead sees an invalid `F6` context
   before that sequence and skips through the following `00000000 FFFF`.

The single-digit zeros, spaces, `+` separators, `0x` prefixes, and sentinels
are functional. Reformatting the generated `cheat0_code` line can change
ReARMed's line pairing or let one core execute another core's instructions.
These are current-parser behaviors, so core parser changes need a fresh check.

## Review and regeneration

`generate.py` reads the neighboring original `.cht`, checks its Git blob ID,
checks the generated code against the live-tested SHA-256
`02c67e0255c30692c34c513fcd4be336d547676c875db070c478d5f135034115`,
and writes both the loadable cheat and `ANNOTATED.md`. A change to the code
requires a new three-core test before updating this checksum. Run the script
with Python 3.10 or later from this folder:

```text
python generate.py
```

The operation map lists the active `A4` guard and each core's intended
instructions for all 37 source writes. It is explanatory; the loadable cheat
must retain the generated wrappers and separators. The current code string is
10,471 characters. Parser checks counted 395 Beetle commands, 214 supported
ReARMed commands with no incomplete lines, and 798 SwanStation instructions
including no-ops. The local RAM-behavior verifier passed 257 full-source
scenarios twice and 280 isolated per-write cases for NTSC-U 1.2. A native C
harness also exercised Beetle's exact tokenizer with this entry and a larger
1,395-command input. Per-frame performance was not measured.

The original widescreen research is credited to HugoPocked in this
repository's main README; the existing source and this conversion follow the
repository's MIT license. Core behavior references:
[RetroArch cheat guide](https://docs.libretro.com/guides/cheat-codes/),
[Beetle parser](https://github.com/libretro/beetle-psx-libretro/blob/master/libretro.c),
[ReARMed engine](https://github.com/libretro/pcsx_rearmed/blob/master/libpcsxcore/cheat.c),
and [SwanStation engine](https://github.com/libretro/swanstation/blob/main/src/core/cheats.cpp).

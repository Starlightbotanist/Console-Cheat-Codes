"""Regenerate the one-toggle RetroArch code from NTSC-U 1.2.cht.

The output deliberately contains three instruction streams in one code field.
Each core recognizes its own stream and ignores or skips the other two. Keep
the exact separators: PCSX-ReARMed counts them while splitting code pairs.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "NTSC-U 1.2.cht"
CHEAT = HERE / "NTSC-U 1.2 - Universal.cht"
ANNOTATED = HERE / "ANNOTATED.md"
SOURCE_BLOB = "812ebda37489cf48f37dcd2b63f93d06a59e5eb5"
TESTED_CODE_SHA256 = "02c67e0255c30692c34c513fcd4be336d547676c875db070c478d5f135034115"
HEX = "0123456789ABCDEF"
CODE_LINE = re.compile(r"^([0-9A-F]{8}) ([0-9A-F]{4,8})(?: # (.*))?$")
SECTIONS = {
    "Car Selection (Arcade)",
    "Car Selection 2P Battle (Arcade)",
    "Pre-race screen (Arcade)",
    "Race",
    "Race (Rear view mirror)",
    "Post-race screen #1",
    "Bonus screen (Licenses)",
    "Results screen",
    "Post-race screen #2",
    "Bonus screen (Trophy)",
    "GT Mode screens (Simulation)",
}


@dataclass(frozen=True)
class Guard:
    address: int
    value: int


@dataclass(frozen=True)
class Write:
    line: int
    section: str
    guard: Guard
    address: int
    old: int | None  # None means an unconditional 80 write within the A4 block.
    new: int


def read_source() -> list[Write]:
    """Turn A4 blocks, A7 compare/writes and 80 writes into guarded writes."""
    # Git may check the source out with CRLF on Windows. Hash its canonical
    # LF content, which is the reviewed blob, without changing the source file.
    data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
    blob = sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if blob != SOURCE_BLOB:
        raise ValueError(f"The reviewed source changed: {blob}")

    writes: list[Write] = []
    guard: Guard | None = None
    section = ""
    for line_number, raw in enumerate(data.decode("utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("["):
            continue
        if line.startswith("#"):
            heading = line[1:].strip()
            if heading in SECTIONS:
                section = heading
            continue

        match = CODE_LINE.fullmatch(line)
        if not match:
            raise ValueError(f"Unexpected source line {line_number}: {line}")
        code, value, comment = match.groups()
        opcode, address = code[:2], int(code[2:], 16)
        if code == "00000000" and value == "FFFF":
            guard = None
        elif opcode == "A4" and len(value) == 8:
            if guard is not None:
                raise ValueError(f"Nested A4 block at line {line_number}")
            if comment and comment.startswith("Reset the race overlay"):
                section = comment
            guard = Guard(address, int(value, 16))
        elif opcode == "A7" and len(value) == 8 and guard is not None:
            writes.append(Write(
                line_number, section, guard, address,
                int(value[:4], 16), int(value[4:], 16),
            ))
        elif opcode == "80" and len(value) == 4 and guard is not None:
            # The source's four overlay-marker writes all set their word to 0.
            # SwanStation's zero-range F1 instruction expresses that exactly.
            if value != "0000":
                raise ValueError(f"Unexpected nonzero 80 write at line {line_number}")
            writes.append(Write(line_number, section, guard, address, None, 0))
        else:
            raise ValueError(f"Unsupported source code at line {line_number}: {line}")

    if guard is not None or len(writes) != 37:
        raise ValueError(f"Incomplete source: {len(writes)} writes, guard={guard}")
    return writes


def gameshark(opcode: str, address: int, value: int) -> str:
    if not 0 <= address <= 0xFFFFFF or not 0 <= value <= 0xFFFF:
        raise ValueError("GameShark address or value out of range")
    return f"{opcode}{address:06X}+{value:04X}"


def beetle_codes(write: Write) -> list[str]:
    # Beetle stacks consecutive D0 tests. Both halves of the 32-bit A4
    # signature must match, followed by A7's original target word if present.
    codes = [
        gameshark("D0", write.guard.address, write.guard.value & 0xFFFF),
        gameshark("D0", write.guard.address + 2, write.guard.value >> 16),
    ]
    if write.old is not None:
        codes.append(gameshark("D0", write.address, write.old))
    codes.append(gameshark("80", write.address, write.new))
    return codes


def rearmed_codes(write: Write) -> list[str]:
    # ReARMed's failed D0 test skips one instruction, not a whole D0 stack.
    # The D1 checks and zero-length C2 copy form an AND gate for the final 80.
    codes = [
        gameshark("D0", write.guard.address, write.guard.value & 0xFFFF),
        gameshark("D1", write.guard.address + 2, write.guard.value >> 16),
    ]
    if write.old is not None:
        codes.extend((
            gameshark("D1", write.address, write.old),
            gameshark("D1", write.address, write.old),
        ))
    codes.extend((gameshark("C2", 0, 0), gameshark("80", write.address, write.new)))
    return codes


def swan_codes(write: Write) -> list[tuple[int, int]]:
    # SwanStation understands the original A4 block and A7 compare/replace.
    # For an unconditional zero marker, F1 with min=max=0 writes zero.
    action = (
        (0xA7000000 | write.address, (write.old << 16) | write.new)
        if write.old is not None else
        (0xF1000000 | write.address, 0)
    )
    return [(0xA4000000 | write.guard.address, write.guard.value), action, (0, 0xFFFF)]


class Stream:
    """Preserve the even separator parity that ReARMed's frontend requires."""

    def __init__(self) -> None:
        self.fragments: list[str] = []
        self.separators = 0

    def add(self, fragment: str) -> None:
        if self.fragments:
            separator = "  " if self.separators % 2 == 0 else " "
            self.fragments.append(separator)
            self.separators += len(separator)
        assert self.separators % 2 == 0
        self.fragments.append(fragment)
        self.separators += sum(char not in HEX for char in fragment)

    def beetle(self, code: str) -> None:
        # Beetle joins the 8- and 4-digit fields. ReARMed sees two lines with
        # low addresses and ignores them; SwanStation sees two 00 no-ops.
        address, value = code.split("+")
        self.add(f"0+{address}+{value}+0")

    def swan(self, address: int, value: int) -> None:
        # SwanStation accepts 0x-prefixed hex fields. ReARMed splits at each
        # x and ignores the resulting low-address lines. Beetle's hex-token
        # scanner treats the single-digit zeros as boundaries.
        self.add(f"0x{address:08X}+0x{value:08X}")

    def code(self) -> str:
        return "".join(self.fragments)


def compile_write(write: Write) -> str:
    stream = Stream()
    for code in beetle_codes(write):
        stream.beetle(code)
    for address, value in swan_codes(write):
        stream.swan(address, value)

    # An unsigned RAM word cannot be less than zero. Thus Beetle's D2 check
    # stops the following ReARMed C2 dummy patch from writing anything.
    stream.beetle(gameshark("D2", 0, 0))

    # SwanStation's invalid F6 context skips ReARMed instructions through the
    # next 00000000 FFFF. F6 itself is hidden from Beetle and ReARMed.
    stream.swan(0xF6000000, 0)
    stream.add("0+0")  # Drop a pending Beetle 8-digit half before ReARMed D0.
    for code in rearmed_codes(write):
        stream.add(code)
    stream.swan(0, 0xFFFF)
    return stream.code()


def compile_cheat(writes: list[Write]) -> str:
    stream = Stream()
    for write in writes:
        stream.add(compile_write(write))
    return stream.code()


def render_cheat(code: str) -> str:
    return "\n".join((
        "# Gran Turismo 2 NTSC-U 1.2 16:9 widescreen for RetroArch.",
        "# Source: ../NTSC-U 1.2.cht (original A4/A7 code; see README.md).",
        "# One toggle for Beetle PSX, PCSX-ReARMed, and SwanStation.",
        "# Beetle needs streaming cheat parsing; stock 64-token builds truncate this.",
        "# The 0x prefixes, single-digit zeros, pluses and spaces are intentional.",
        "# Generated by generate.py; see ANNOTATED.md for every source write.",
        "cheats = 1",
        "",
        'cheat0_desc = "GT2 NTSC-U 1.2 16:9 Universal"',
        f'cheat0_code = "{code}"',
        "cheat0_enable = false",
        "cheat0_handler = 0",
        "",
    ))


def render_annotated(writes: list[Write]) -> str:
    lines = [
        "# NTSC-U 1.2: source-write map",
        "",
        "Each numbered item maps one original source write to the instructions",
        "that each core is meant to execute. These are **not** pasteable cheat",
        "strings: the generated `.cht` wraps and hides each stream as described",
        "in [README.md](README.md). Source line numbers refer to",
        "[`../NTSC-U 1.2.cht`](../NTSC-U%201.2.cht).",
        "",
    ]
    section = None
    for index, write in enumerate(writes, 1):
        if write.section != section:
            section = write.section
            lines.extend((f"## {section}", ""))
        original = (
            f"A7{write.address:06X} {write.old:04X}{write.new:04X}"
            if write.old is not None else
            f"80{write.address:06X} {write.new:04X}"
        )
        swan = " ".join(f"{address:08X}+{value:08X}" for address, value in swan_codes(write))
        lines.extend((
            f"### {index}. Source line {write.line}: `{original}`",
            "",
            f"- Active A4 signature: `A4{write.guard.address:06X} {write.guard.value:08X}`.",
            f"- Beetle: `{' '.join(beetle_codes(write))}`.",
            f"- SwanStation: `{swan}`.",
            f"- PCSX-ReARMed: `{' '.join(rearmed_codes(write))}`.",
            "",
        ))
    return "\n".join(lines)


def main() -> None:
    writes = read_source()
    code = compile_cheat(writes)
    # Any generator edit that changes the live-tested code needs review and a
    # new three-core test before this reference checksum can be updated.
    digest = sha256(code.encode("ascii")).hexdigest()
    if digest != TESTED_CODE_SHA256:
        raise ValueError(f"Generated code differs from the tested code: {digest}")
    CHEAT.write_bytes(render_cheat(code).encode("utf-8"))
    ANNOTATED.write_bytes(render_annotated(writes).encode("utf-8"))
    print(f"Wrote {len(writes)} annotated writes and {len(code)} code characters")


if __name__ == "__main__":
    main()

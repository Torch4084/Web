#!/usr/bin/env python3
"""
Nostalgia extraction chain.

The challenge is a Scratch project (.sb3) that wraps a complete RV32 Linux
machine. The "interesting" data lives in three nested layers:

  1. nostalgia.sb3 is a ZIP archive. Inside is a 177 MB project.json plus
     a handful of tiny assets.
  2. project.json stores the guest ROM as a list of decimal strings
     (RISCV.ROM = ["123", "45", "67", ...]) instead of raw bytes. That
     string encoding is what blows the JSON up to 177 MB. The full JSON
     parse is unnecessary. We memory-map the file, locate the RISCV.ROM
     list with a simple string search, and convert the numeric strings
     to raw bytes directly.
  3. The resulting rom.bin is a RISC-V Linux image. The interesting part
     is an embedded newc CPIO initramfs at offset 0x191100. Parse the
     110-byte newc header, walk the 4-byte-aligned entries, and write
     each file to disk.

The flag is at root/readme.txt inside the extracted filesystem.

Usage:
  python3 nostalgia_extract.py                     # uses default paths
  python3 nostalgia_extract.py /path/to/nostalgia.sb3 /path/to/output
"""

import mmap
import os
import re
import sys
import zipfile
from pathlib import Path

ROM_MARKER = b'["RISCV.ROM",['
NEWC_MAGIC = b'070701'

def align4(v):
    return (v + 3) & ~3

def extract_project_json(sb3_path, workdir):
    """Unzip nostalgia.sb3 and return the path to project.json."""
    with zipfile.ZipFile(sb3_path) as z:
        members = z.namelist()
        if 'project.json' not in members:
            raise SystemExit("project.json not found in archive")
        z.extract('project.json', path=workdir)
    return Path(workdir) / 'project.json'

def extract_rom(project_json_path, output_path):
    """Memory-map project.json, locate the RISCV.ROM list, write the
    raw byte stream. Returns the number of bytes written."""
    with project_json_path.open('rb') as f:
        data = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            start = data.find(ROM_MARKER)
            if start < 0:
                raise SystemExit("RISCV.ROM marker not found")
            start += len(ROM_MARKER)
            end = data.find(b']]', start)
            if end < 0:
                raise SystemExit("end of RISCV.ROM list not found")
            pattern = re.compile(rb'"([0-9]+)"')
            rom = bytes(int(m.group(1)) for m in pattern.finditer(data, start, end))
        finally:
            data.close()
    output_path.write_bytes(rom)
    return len(rom)

def parse_initramfs(rom_bytes, output_dir):
    """Parse a newc CPIO initramfs from the given byte stream, write
    all files under output_dir. Returns (entry_count, last_offset)."""
    out_files = []
    cursor = 0x191100
    if rom_bytes[cursor:cursor+6] != NEWC_MAGIC:
        raise SystemExit("expected newc magic at 0x191100")
    while cursor < len(rom_bytes) and rom_bytes[cursor:cursor+6] == NEWC_MAGIC:
        header = rom_bytes[cursor:cursor+110]
        fields = [int(header[6 + i*8:14 + i*8], 16) for i in range(13)]
        size = fields[6]
        name_size = fields[11]
        name_start = cursor + 110
        name = rom_bytes[name_start:name_start + name_size - 1].decode(errors='replace')
        data_start = align4(name_start + name_size)
        data_end = data_start + size
        if name == 'TRAILER!!!':
            cursor = data_end
            break
        if name and name != '.':
            parts = name.strip('/').split('/')
            out_path = os.path.join(output_dir, *parts)
            if name.endswith('/') or size == 0 and not parts[-1]:
                os.makedirs(out_path, exist_ok=True)
            else:
                parent = os.path.dirname(out_path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                if size > 0:
                    Path(out_path).write_bytes(rom_bytes[data_start:data_end])
        out_files.append(name)
        cursor = align4(data_end)
    return len(out_files), cursor

def find_flag(rootfs_dir):
    """Search the extracted filesystem for a readme.txt / flag file."""
    candidates = []
    root = Path(rootfs_dir)
    for p in root.rglob('readme*'):
        candidates.append(p)
    for p in root.rglob('flag*'):
        candidates.append(p)
    for p in candidates:
        try:
            text = p.read_text(errors='replace')
            if 'OmniCTF' in text or 'omniCTF' in text or 'OMNICTF' in text:
                return p, text
        except Exception:
            continue
    return None, None

def main():
    sb3 = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\user\Downloads\nostalgia.sb3"
    out = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\user\Downloads\CTFwriteups\Nostalgia\extracted"
    Path(out).mkdir(parents=True, exist_ok=True)

    print(f"[*] Reading: {sb3}")
    pj = extract_project_json(sb3, out)
    print(f"[*] project.json: {pj.stat().st_size:,} bytes")

    rom_path = Path(out) / 'rom.bin'
    n = extract_rom(pj, rom_path)
    print(f"[*] ROM: {n:,} bytes -> {rom_path}")

    rom = rom_path.read_bytes()
    rootfs = Path(out) / 'rootfs'
    if rootfs.exists():
        import shutil
        shutil.rmtree(rootfs)
    rootfs.mkdir(parents=True, exist_ok=True)
    entries, end = parse_initramfs(rom, str(rootfs))
    print(f"[*] initramfs: {entries} entries, end at 0x{end:x}")

    flag_path, flag_text = find_flag(str(rootfs))
    if flag_path:
        print(f"\n[+] Flag file: {flag_path}")
        print(f"    Content: {flag_text!r}")
    else:
        print("\n[-] Flag not found in extracted filesystem")

if __name__ == '__main__':
    main()

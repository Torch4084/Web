#!/usr/bin/env python3
"""
Generates a minimal valid Windows x64 PE (MZ/PE stub) as exploit_m2.exe
so that solve.py has a payload file to send.
"""
import struct, os

OUT = os.path.join(os.path.dirname(__file__), "exploit_m2.exe")

# Tiny x64 code stub: xor ecx,ecx / xor eax,eax (just nops out - for blob purposes only)
CODE = bytes([0x33, 0xC9, 0x33, 0xC0, 0xC3])  # xor ecx,ecx / xor eax,eax / ret
CODE = CODE.ljust(0x200, b'\x00')

FILE_ALIGN    = 0x200
SECTION_ALIGN = 0x1000
IMAGE_BASE    = 0x140000000
CODE_RVA      = 0x1000
PE_OFFSET     = 0x40

# DOS stub
dos = bytearray(PE_OFFSET)
dos[0:2]     = b'MZ'
struct.pack_into('<I', dos, 0x3C, PE_OFFSET)  # e_lfanew

# COFF file header
coff = struct.pack('<HHIIIHH',
    0x8664,  # Machine = AMD64
    1,       # NumberOfSections
    0,       # TimeDateStamp
    0,       # PointerToSymbolTable
    0,       # NumberOfSymbols
    0xF0,    # SizeOfOptionalHeader
    0x0022,  # Characteristics: executable
)

# Optional header (PE32+) — build field by field to avoid format confusion
opt = bytearray(0xF0)
struct.pack_into('<H',   opt, 0x00, 0x020B)        # Magic PE32+
struct.pack_into('<B',   opt, 0x02, 14)             # MajorLinkerVersion
struct.pack_into('<B',   opt, 0x03, 0)              # MinorLinkerVersion
struct.pack_into('<I',   opt, 0x04, len(CODE))      # SizeOfCode
struct.pack_into('<I',   opt, 0x08, 0)              # SizeOfInitializedData
struct.pack_into('<I',   opt, 0x0C, 0)              # SizeOfUninitializedData
struct.pack_into('<I',   opt, 0x10, CODE_RVA)       # AddressOfEntryPoint
struct.pack_into('<I',   opt, 0x14, CODE_RVA)       # BaseOfCode
struct.pack_into('<Q',   opt, 0x18, IMAGE_BASE)     # ImageBase
struct.pack_into('<I',   opt, 0x20, SECTION_ALIGN)  # SectionAlignment
struct.pack_into('<I',   opt, 0x24, FILE_ALIGN)     # FileAlignment
struct.pack_into('<H',   opt, 0x28, 6)              # MajorOSVersion
struct.pack_into('<H',   opt, 0x2A, 0)              # MinorOSVersion
struct.pack_into('<H',   opt, 0x2C, 0)              # MajorImageVersion
struct.pack_into('<H',   opt, 0x2E, 0)              # MinorImageVersion
struct.pack_into('<H',   opt, 0x30, 6)              # MajorSubsystemVersion
struct.pack_into('<H',   opt, 0x32, 0)              # MinorSubsystemVersion
struct.pack_into('<I',   opt, 0x38, CODE_RVA + SECTION_ALIGN)  # SizeOfImage
struct.pack_into('<I',   opt, 0x3C, FILE_ALIGN)     # SizeOfHeaders
struct.pack_into('<H',   opt, 0x44, 3)              # Subsystem = Console
struct.pack_into('<Q',   opt, 0x48, 0x100000)       # SizeOfStackReserve
struct.pack_into('<Q',   opt, 0x50, 0x1000)         # SizeOfStackCommit
struct.pack_into('<Q',   opt, 0x58, 0x100000)       # SizeOfHeapReserve
struct.pack_into('<Q',   opt, 0x60, 0x1000)         # SizeOfHeapCommit
struct.pack_into('<I',   opt, 0x6C, 16)             # NumberOfRvaAndSizes

# Section header .text
section = struct.pack('<8sIIIIIIHHI',
    b'.text\x00\x00\x00',  # Name
    len(CODE),              # VirtualSize
    CODE_RVA,               # VirtualAddress
    FILE_ALIGN,             # SizeOfRawData
    FILE_ALIGN,             # PointerToRawData  (at offset 0x200)
    0, 0,                   # PointerToRelocations / Linenumbers
    0, 0,                   # Number of relocations / linenumbers
    0x60000020,             # Characteristics: CODE | EXECUTE | READ
)

# Assemble the final binary
headers_size = PE_OFFSET + 4 + len(coff) + len(opt) + len(section)
raw_data_offset = FILE_ALIGN  # pad headers to first FILE_ALIGN boundary

buf = bytearray(FILE_ALIGN + FILE_ALIGN)
buf[0:PE_OFFSET]   = dos
offset = PE_OFFSET
buf[offset:offset+4]        = b'PE\x00\x00';  offset += 4
buf[offset:offset+len(coff)] = coff;           offset += len(coff)
buf[offset:offset+len(opt)]  = opt;            offset += len(opt)
buf[offset:offset+len(section)] = section

buf[raw_data_offset:raw_data_offset+len(CODE)] = CODE

with open(OUT, 'wb') as f:
    f.write(bytes(buf))
print(f"[+] wrote {OUT} ({len(buf)} bytes)")

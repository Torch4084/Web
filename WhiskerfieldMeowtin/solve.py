import socket
import ssl
import re
import argparse

KEYSTREAM = bytes.fromhex("83125936c8931541759c0fcaa6c8b9ac13ed8055d413f2b7f083e9c06173e30d6187b66f40adcd4cad3f92914bfc7d")
MODULUS = 65537

def xor_bytes(a, b):
    return bytes([x ^ y for x, y in zip(a, b)])

def solve():
    parser = argparse.ArgumentParser()
    parser.add_argument("host", nargs="?", default="whiskerfield-89ac38e649ee.inst.omnictf.com")
    parser.add_argument("port", nargs="?", type=int, default=1337)
    args = parser.parse_args()
    
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    print(f"[*] Connecting to {args.host}:{args.port}")
    try:
        sock = socket.create_connection((args.host, args.port), timeout=10)
        sock = context.wrap_socket(sock, server_hostname=args.host)
    except Exception as e:
        print(f"[-] Connection failed: {e}")
        return

    f = sock.makefile('rw', encoding='utf-8')
    
    # Read until tx>
    buffer = ""
    while "tx>" not in buffer:
        line = f.read(1)
        if not line:
            break
        buffer += line

    if "tx>" not in buffer:
        print("[-] Did not find prompt tx>")
        return

    # Extract the hex dump of A
    hex_lines = re.findall(r'00[0-9a-f]{2}:\s*(.*)', buffer)
    hex_str = "".join(hex_lines).replace(" ", "")
    if not hex_str:
        print("[-] Failed to find hex dump")
        return
        
    print(f"[*] Captured A: {hex_str}")
    A_bytes = bytearray.fromhex(hex_str)
    
    patch_offset = -1
    patch_val = -1
    
    for offset in range(len(A_bytes)):
        orig = A_bytes[offset]
        for val in range(256):
            if val == orig:
                continue
            test_bytes = bytearray(A_bytes)
            test_bytes[offset] = val
            test_int = int.from_bytes(test_bytes, "big")
            if test_int % MODULUS == 0:
                patch_offset = offset
                patch_val = val
                break
        if patch_offset != -1:
            break
            
    if patch_offset == -1:
        print("[-] Failed to find a valid patch")
        return
        
    patch_str = f"{patch_offset:x}:{patch_val:02x}\n"
    print(f"[*] Found patch! Offset: {patch_offset}, Value: {patch_val:02x}")
    print(f"[*] Sending patch: {patch_str.strip()}")
    
    sock.sendall(patch_str.encode())
    
    # Read the rest of the output
    out_buf = ""
    while True:
        try:
            sock.settimeout(2.0)
            chunk = sock.recv(4096).decode()
            if not chunk:
                break
            out_buf += chunk
        except socket.timeout:
            break

    # The payload is the LAST hex dump block in the output
    # First hex dump block in out_buf is the patched A.
    # Second hex dump block is the encrypted flag!
    
    blocks = out_buf.split("0000:")[1:]
    if len(blocks) < 2:
        print("[-] Failed to find payload hex dump")
        return
        
    payload_block = "0000:" + blocks[-1]
    payload_hex_lines = re.findall(r'00[0-9a-f]{2}:\s*(.*)', payload_block)
    payload_hex = "".join(payload_hex_lines).replace(" ", "")
    
    print(f"[*] Payload: {payload_hex}")
    
    payload = bytes.fromhex(payload_hex)
    flag = xor_bytes(payload, KEYSTREAM)
    print(f"[+] Decrypted Flag: {flag.decode(errors='replace')}")

if __name__ == "__main__":
    solve()

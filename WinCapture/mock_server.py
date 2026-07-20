#!/usr/bin/env python3
"""
Local mock server simulating the WinCapture challenge server.
Receives a Base64-encoded binary, decodes it, pretends to run it,
then returns a fake flag so the solver pipeline can be verified.
"""
import base64
import socket
import threading
import sys

HOST = "127.0.0.1"
PORT = 14337

BANNER = b"Waiting for exploit.exe\n"
FAKE_FLAG = b"OmniCTF{r4c1ng_th3_k3rn3l_1s_fun_1f_y0u_w1n}\n"


def handle(conn: socket.socket, addr):
    print(f"[mock] connection from {addr}")
    try:
        conn.sendall(BANNER)

        # Read base64 lines until "END"
        buf = bytearray()
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
            if b"END\n" in buf:
                break

        lines = buf.split(b"\n")
        b64 = b"".join(l for l in lines if l and l != b"END")
        blob = base64.b64decode(b64)
        print(f"[mock] received {len(blob)} bytes of payload")

        # Simulate driver interaction output
        conn.sendall(b"[driver] stage_alloc: OK\r\n")
        conn.sendall(b"[driver] key_alloc: OK\r\n")
        conn.sendall(b"[driver] racing commit...\r\n")
        conn.sendall(b"[driver] TOCTOU window hit after 17 attempts\r\n")
        conn.sendall(b"[driver] key object forged, authorization granted\r\n")
        conn.sendall(b"flag: " + FAKE_FLAG)

    except Exception as e:
        print(f"[mock] error: {e}")
    finally:
        conn.close()
        print("[mock] connection closed")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(5)
        print(f"[mock] WinCapture mock server listening on {HOST}:{PORT}")
        print("[mock] Press Ctrl+C to stop\n")
        try:
            while True:
                conn, addr = srv.accept()
                t = threading.Thread(target=handle, args=(conn, addr), daemon=True)
                t.start()
        except KeyboardInterrupt:
            print("\n[mock] shutting down")


if __name__ == "__main__":
    main()

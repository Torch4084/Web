import socket
import ssl
import json
import subprocess
import os
import time

host = 'orbital-caa083d42cbd.inst.omnictf.com'
port = 1337

context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

with socket.create_connection((host, port)) as sock:
    with context.wrap_socket(sock, server_hostname=host) as ssock:
        data = b''
        while b"Authorize orbital strike cannon using 128-bit firing code (hex):" not in data:
            chunk = ssock.recv(4096)
            if not chunk:
                break
            data += chunk
            
        print("Received data from server")
        # Extract the JSON part
        text = data.decode('utf-8', errors='ignore')
        json_str = ""
        in_json = False
        lines = []
        for line in text.split('\n'):
            if line.startswith('{'):
                in_json = True
            if in_json:
                lines.append(line)
            if line.startswith('}'):
                in_json = False
                break
                
        json_str = '\n'.join(lines)
        with open('public.json', 'w') as f:
            f.write(json_str)
            
        print("Wrote public.json, running solver...")
        solver_path = r'C:\Users\user\Downloads\OmniCTF-Full-Writeups\solvers\14_orbital_strike_telemetry.py'
        result = subprocess.run(['python', solver_path, 'public.json'], capture_output=True, text=True)
        print("Solver output:")
        print(result.stdout)
        
        # Extract the firing code
        code = None
        for line in result.stdout.split('\n'):
            if "firing code =" in line:
                code = line.split('=')[1].strip()
                break
        
        if code:
            print(f"Sending code: {code}")
            ssock.sendall((code + "\n").encode())
            
            # Read flag
            time.sleep(1)
            resp = ssock.recv(4096).decode('utf-8', errors='ignore')
            print("Server response:")
            print(resp)
        else:
            print("Failed to get firing code.")

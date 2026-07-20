import socket, ssl, re, sys, time

HOST, PORT = "baccarat-fd4989e35cae.inst.omnictf.com", 1337
TARGET = 100000

FAVORED = {
    ("OmniCybr",  "BlackShard"): "player",
    ("BlackShard", "OmniCybr"):  "banker",
    ("NorthStar",  "BlackShard"): "player",
    ("BlackShard", "NorthStar"):  "banker",
    ("NipCat",     "BlackShard"): "player",
    ("BlackShard", "NipCat"):     "banker",
    ("VoltaicAI",  "BlackShard"): "player",
    ("BlackShard", "VoltaicAI"):  "banker",
    ("OmniCybr",   "VoltaicAI"):  "player",
    ("VoltaicAI",  "OmniCybr"):   "banker",
    ("VoltaicAI",  "NorthStar"):  "banker",
    ("NorthStar",  "VoltaicAI"):  "player",
}

def open_session():
    raw = socket.create_connection((HOST, PORT), timeout=30)
    ctx = ssl.create_default_context()
    s = ctx.wrap_socket(raw, server_hostname=HOST)
    s.settimeout(30)
    return s

def play():
    s = open_session()
    f = s.makefile("rwb", buffering=0)
    player = banker = None
    bankroll = 0

    while True:
        try:
            line = f.readline()
        except Exception:
            s.close()
            return False
        if not line:
            s.close()
            return False
        text = line.decode(errors="replace").strip()

        m = re.match(r"BankerAI :: (\S+)", text)
        if m:
            banker = m.group(1)
        m = re.match(r"PlayerAI :: (\S+)", text)
        if m:
            player = m.group(1)
        m = re.match(r"Bankroll :: (\d+)", text)
        if m:
            bankroll = int(m.group(1))
            if bankroll >= TARGET:
                # Server sends: Session result :: bankroll target reached
                # then:            FLAG :: <flag>
                # Read until we see FLAG ::
                flag = None
                for _ in range(5):
                    try:
                        fl = f.readline()
                    except:
                        break
                    if not fl:
                        break
                    decoded = fl.decode(errors="replace").strip()
                    if "FLAG ::" in decoded:
                        flag = decoded.replace("FLAG ::", "").strip()
                    elif "omni{" in decoded or "flag{" in decoded:
                        flag = decoded
                if flag:
                    print(f"FLAG :: {flag}")
                s.close()
                return True

        if text.startswith("Bet side"):
            side = FAVORED[(player, banker)]
            f.write((side + "\n").encode())
            f.flush()

        if text.startswith("Bet amount"):
            amount = min(bankroll, TARGET - bankroll)
            f.write((str(amount) + "\n").encode())
            f.flush()

if __name__ == "__main__":
    for session in range(100):
        try:
            if play():
                break
        except Exception as e:
            print(f"  session {session+1} failed: {e}", file=sys.stderr)
        time.sleep(0.2)

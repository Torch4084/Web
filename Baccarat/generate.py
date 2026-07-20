#!/usr/bin/env python
"""
Baccarat misc writeup generator.

Misc challenge with a real betting solver. Pages:
  - HUD
  - brief
  - triage (server.py + game.py recon)
  - favored-side lookup (tournament_stats.py)
  - bold bet sizing (the math)
  - sim (the auto-betting progression simulator)
  - signal map (12 matchup edges)
  - flag
  - appendix (full solver source)
"""
import os
import re

TEMPLATE = r'C:\Users\user\Downloads\CTFwriteups\Kant\kant-writeup.html'
OUT      = r'C:\Users\user\Downloads\CTFwriteups\Baccarat\baccarat-writeup.html'

# Theme: purple palette
ACCENT       = '#b57aff'
ACCENT_RGB   = '181, 122, 255'
ACCENT_DIM   = 'rgba(181, 122, 255, 0.12)'
ACCENT_LINE  = 'rgba(181, 122, 255, 0.24)'
ROOT         = '#1e1038'
PANEL_RGBA   = 'rgba(10, 6, 20, 0.84)'
LINE_RGBA    = 'rgba(181, 122, 255, 0.24)'
BG           = '#06030e'
TEXT         = '#e8e0f0'
MUTED        = '#8a7a9c'
GOOD         = '#b57aff'
BAD          = '#ff6b6b'
INFO         = '#6bb6ff'

CHALLENGE = 'Baccarat'
FLAG      = 'omni{baccarat_kelly_goes_brrrr_6da7b1f}'

with open(TEMPLATE, 'r', encoding='utf-8') as f:
    html = f.read()

# ----------------------------------------------------------------------------
# 1. Head + theme
# ----------------------------------------------------------------------------
html = html.replace(
    '<title>KANT // REVERSIBLE CHECKER INVERSION</title>',
    '<title>BACCARAT // BOLD-BETTING ON A FAVORED SIDE</title>'
)
html = html.replace(
    '<meta name="description" content="OmniCTF 2026 // Kant writeup // Reverse engineering a 12-layer reversible 36-byte checker, with HUD chrome, live solver, and signal map.">',
    '<meta name="description" content="OmniCTF 2026 // Baccarat writeup // Learning favored AI matchups and growing a 1000-coin bankroll to 100000 with bold bet sizing.">'
)
html = html.replace('<meta name="theme-color" content="#ff9d00">',
                    '<meta name="theme-color" content="#5dff9d">')
html = html.replace('%23ff9d00', '%235dff9d')
html = html.replace('>K</text>', '>B</text>')

old_root = re.search(r':root\s*\{[^}]*\}', html, re.DOTALL).group(0)
new_root = f""":root {{
    --accent: {ACCENT};
    --accent-rgb: {ACCENT_RGB};
    --accent-dim: {ACCENT_DIM};
    --accent-line: {ACCENT_LINE};
    --root: {ROOT};
    --bg: {BG};
    --panel: {PANEL_RGBA};
    --panel-strong: rgba(6, 12, 8, 0.94);
    --line: {LINE_RGBA};
    --text: {TEXT};
    --muted: {MUTED};
    --good: {GOOD};
    --bad: {BAD};
    --info: {INFO};
    --font-mono: "JetBrains Mono", ui-monospace, Menlo, monospace;
    --font-display: "Rajdhani", system-ui, sans-serif;
  }}"""
html = html.replace(old_root, new_root)

html = html.replace(
    'radial-gradient(1200px 600px at 12% -10%, rgba(255,157,0,0.10), transparent 60%)',
    'radial-gradient(1200px 600px at 12% -10%, rgba(93,255,157,0.10), transparent 60%)'
)
html = html.replace(
    'radial-gradient(900px 500px at 110% 10%, rgba(255,48,48,0.06), transparent 70%)',
    'radial-gradient(900px 500px at 110% 10%, rgba(26,58,38,0.10), transparent 70%)'
)
html = html.replace(
    'repeating-linear-gradient(0deg, rgba(255,157,0,0.025) 0 1px, transparent 1px 3px)',
    'repeating-linear-gradient(0deg, rgba(93,255,157,0.025) 0 1px, transparent 1px 3px)'
)
html = re.sub(r'rgba\(255,\s*157,\s*0,\s*([^)]+)\)',
              lambda m: f'rgba(93, 255, 157, {m.group(1)})', html)
html = html.replace('#ffd28a', '#d6ffe6')
html = html.replace('--root: #ff3030;', f'--root: {ROOT};')

# ----------------------------------------------------------------------------
# 2. Remove the leftover kant_solver.js script tag (Kant template artifact;
#    this writeup has its own solver, no kant_solver.js)
# ----------------------------------------------------------------------------
html = re.sub(r'<script src="kant_solver\.js"></script>', '', html)

# Also strip the inline sim controller script (Kant wired it up to a 12-layer
# solver; this writeup uses a betting sim, not the kant solver). We find the
# script that starts with the "Kant live solver simulator" comment and remove
# the whole <script>...</script> block.
html = re.sub(
    r'<script>\s*\n//\s*={20,}\s*\n//\s*Kant live solver simulator.*?</script>',
    '',
    html,
    flags=re.DOTALL,
)
# Fallback: if the regex misses (whitespace/quoting differences), do a manual scan.
if 'Kant live solver simulator' in html:
    i = html.find('Kant live solver simulator')
    i_open = html.rfind('<script>', 0, i)
    i_close = html.find('</script>', i) + len('</script>')
    html = html[:i_open] + html[i_close:]

# ----------------------------------------------------------------------------
# 3. CSS additions
# ----------------------------------------------------------------------------
extra_css = '''
/* Bet table (favored side lookup) */
.bet-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 14px 0;
  font-size: 12.5px;
}
.bet-table th, .bet-table td {
  padding: 8px 10px;
  border: 1px solid var(--accent-line);
  text-align: left;
}
.bet-table th {
  background: rgba(0,0,0,0.4);
  color: var(--accent);
  font-family: var(--font-display);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  font-size: 10.5px;
}
.bet-table td {
  background: rgba(0,0,0,0.32);
  font-family: var(--font-mono);
}
.bet-table .side-player { color: #5dff9d; font-weight: 700; }
.bet-table .side-banker { color: #ff9d5d; font-weight: 700; }

/* Banner banner block (server protocol excerpt) */
.protocol {
  border: 1px solid var(--accent-line);
  background: rgba(0,0,0,0.42);
  padding: 12px 14px;
  margin: 12px 0;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
}
.protocol b { color: var(--accent); }

/* Bold-bet step ladder */
.ladder {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 14px 0;
}
.ladder .step {
  border: 1px solid var(--accent-line);
  background: rgba(0,0,0,0.42);
  padding: 10px 12px;
  flex: 1;
  min-width: 110px;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 12px;
}
.ladder .step .amt { color: var(--accent); font-weight: 800; font-size: 16px; }
.ladder .step .lbl { color: var(--muted); font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase; margin-top: 4px; }
.ladder .step.final { border-color: var(--good); }
.ladder .step.final .amt { color: var(--good); }

/* Map arrow markers colored via CSS so they pick up the theme accent */
.map-wrap marker path { fill: var(--accent); transition: fill .3s; }
.map-wrap marker[id="arr-faint"] path { fill: #7f766a; }
'''
html = html.replace('</style>', extra_css + '\n</style>')

# ----------------------------------------------------------------------------
# 4. Rebuild the body
# ----------------------------------------------------------------------------
body_start = html.find('<body>')
body_end   = html.rfind('</body>')

NEW_BODY = '''
  <header class="hud" role="banner">
    <div class="brand">
      <span class="mark">B</span>
      <span>BACCARAT // WRITEUP</span>
    </div>
    <nav class="nav" aria-label="Sections">
      <a href="#brief">brief</a>
      <a href="#triage">triage</a>
      <a href="#favored">favored side</a>
      <a href="#sizing">bet sizing</a>
      <a href="#solver">solver</a>
      <a href="#sim">sim</a>
      <a href="#signal">signal</a>
      <a href="#flag">flag</a>
    </nav>
    <div class="status">
      <span class="chip ok"><span class="dot"></span>solved</span>
      <span class="chip"><span class="dot"></span>misc // betting</span>
      <span class="chip">omni 2026</span>
    </div>
  </header>

  <main>
    <section class="brief" id="brief">
      <div class="panel">
        <div class="sub">// root // challenge misc // omnictf 2026</div>
        <h1>Baccarat &mdash; seven wins to the flag</h1>
        <p class="lede">The goal is to learn which side is favored for each visible matchup, then size even-money bets well enough to grow the bankroll to the target. I start at 1000 coins, I need 100000, and the only edge I have is knowing which AI pairing favors which side.</p>
        <p>I pull the simulator output, build a static lookup table, and run a TLS client that sends the favored side with a bold bet every round. Seven consecutive wins on favorable tables clears the target and the server prints the flag.</p>
        <div class="row-flex" style="margin-top:10px">
          <span class="chip ok"><span class="dot"></span>flag recovered</span>
          <span class="chip"><span class="dot"></span>12 matchups</span>
          <span class="chip"><span class="dot"></span>bold play sizing</span>
          <span class="chip bad"><span class="dot"></span>7 wins or bust</span>
        </div>
      </div>
      <div class="panel">
        <div class="sub">// challenge matrix</div>
        <div class="grid-2">
          <div class="row"><span class="k">artifact</span><span class="v">baccarat-player.zip</span></div>
          <div class="row"><span class="k">service</span><span class="v accent">ncat --ssl ...1337</span></div>
          <div class="row"><span class="k">category</span><span class="v">miscellaneous // 61 pts</span></div>
          <div class="row"><span class="k">flag format</span><span class="v bad">omni&#123;kelly_...&#125;</span></div>
          <div class="row"><span class="k">approach</span><span class="v">tournament_stats &rarr; lookup &rarr; bold bets</span></div>
          <div class="row"><span class="k">time to solve</span><span class="v">~30 min</span></div>
          <div class="row"><span class="k">core idea</span><span class="v">find the edge, bet everything</span></div>
          <div class="row"><span class="k">flag</span><span class="v accent">{FLAG}</span></div>
        </div>
      </div>
    </section>

    <section id="triage">
      <div class="sec-head">
        <span class="idx">01 //</span>
        <h2>triage &mdash; what the service leaks</h2>
        <span class="tag">phase / recon</span>
      </div>
      <div class="panel prose">
        <p>The service is a TLS-on-TCP protocol. I connect, the banner prints, and then every round gives me the two AI names plus the current bankroll before asking for a side and a bet amount. Here's the prompt sequence I see:</p>
        <div class="protocol"><b>Round N of M
BankerAI :: &lt;name&gt;
PlayerAI :: &lt;name&gt;
Bankroll :: &lt;coins&gt;
Bet side [player/banker]:</b>
&gt; player
<b>Bet amount [1-&lt;bankroll&gt;] (or 'all'):</b>
&gt; 1000
<b>Outcome :: player wins (3-1) :: bankroll 2000</b></div>
        <p>Two things are leaking here. First, the names tell me which duel is about to play, so I can pre-load the favored side. Second, the bankroll leak is what makes bold sizing possible. If I didn't see the bankroll I'd be guessing. Ties are replayed internally until a real winner shows, so the round counter and my bankroll both advance by exactly one resolved bet.</p>
        <p>Three constants in <code>server.py</code> drive the whole challenge:</p>
        <div class="protocol"><b>START_BANKROLL = 1000
TARGET_BANKROLL = 100000
ROUNDS_PER_TABLE = 12</b></div>
        <p>Payout is even money. One resolved bet on the favored side, sized right, doubles the bankroll. Seven in a row clears the target. The <code>ROUNDS_PER_TABLE = 12</code> is what stops me from farming a single table forever; the AI matchup will rotate, so I want the bankroll target hit before rotation breaks my favored-side edge.</p>
      </div>
    </section>

    <section id="favored">
      <div class="sec-head">
        <span class="idx">02 //</span>
        <h2>favored side &mdash; tournament_stats on the agent pool</h2>
        <span class="tag">phase / analysis</span>
      </div>
      <div class="panel prose">
        <p>The archive ships a 10000-round per-matchup simulator. I run it from the extracted challenge folder:</p>
        <div class="protocol"><b>$ python3 tournament_stats.py</b></div>
        <p>It walks the table roster in <code>server.py</code>, simulates each player/banker combination 10000 times, and prints the win rates. The roster only contains matchups with a real edge; the other coin-flip duels were dropped at design time, because the bankroll would never grow on them. The simulator output is short and stable enough that I can re-run it offline and paste the result into a static lookup table.</p>
        <p>Here's the favored-side table I built from the run, in order of strongest edge first:</p>
        <table class="bet-table">
          <thead>
            <tr><th>Player AI</th><th>Banker AI</th><th>Favored bet</th><th>Observed win rate</th></tr>
          </thead>
          <tbody>
            <tr><td>OmniCybr</td><td>BlackShard</td><td class="side-player">player</td><td>~57.7%</td></tr>
            <tr><td>NorthStar</td><td>BlackShard</td><td class="side-player">player</td><td>~57.1%</td></tr>
            <tr><td>BlackShard</td><td>NorthStar</td><td class="side-banker">banker</td><td>~57.4%</td></tr>
            <tr><td>NipCat</td><td>BlackShard</td><td class="side-player">player</td><td>~56.2%</td></tr>
            <tr><td>BlackShard</td><td>NipCat</td><td class="side-banker">banker</td><td>~55.5%</td></tr>
            <tr><td>VoltaicAI</td><td>BlackShard</td><td class="side-player">player</td><td>~54.9%</td></tr>
            <tr><td>BlackShard</td><td>VoltaicAI</td><td class="side-banker">banker</td><td>~52.5%</td></tr>
            <tr><td>OmniCybr</td><td>VoltaicAI</td><td class="side-player">player</td><td>~52.8%</td></tr>
            <tr><td>VoltaicAI</td><td>OmniCybr</td><td class="side-banker">banker</td><td>~52.3%</td></tr>
            <tr><td>VoltaicAI</td><td>NorthStar</td><td class="side-banker">banker</td><td>~52.6%</td></tr>
            <tr><td>NorthStar</td><td>VoltaicAI</td><td class="side-player">player</td><td>~52.1%</td></tr>
          </tbody>
        </table>
        <p>The exact percentages are stochastic, so a re-run on a different seed shifts the last decimal. What survives any re-run is the binary choice: player or banker. That's the part I actually need, so I'm fine with the noise.</p>
      </div>
    </section>

    <section id="sizing">
      <div class="sec-head">
        <span class="idx">03 //</span>
        <h2>bet sizing &mdash; bold play, seven doubles, one partial</h2>
        <span class="tag">phase / math</span>
      </div>
      <div class="panel prose">
        <p>Even-money payout means a winning bet returns the stake plus a matching amount. If I bet the entire bankroll on a win, the bankroll doubles. Starting from 1000, the ladder is:</p>
        <div class="ladder">
          <div class="step"><div class="amt">1000</div><div class="lbl">start</div></div>
          <div class="step"><div class="amt">2000</div><div class="lbl">win #1</div></div>
          <div class="step"><div class="amt">4000</div><div class="lbl">win #2</div></div>
          <div class="step"><div class="amt">8000</div><div class="lbl">win #3</div></div>
          <div class="step"><div class="amt">16000</div><div class="lbl">win #4</div></div>
          <div class="step"><div class="amt">32000</div><div class="lbl">win #5</div></div>
          <div class="step"><div class="amt">64000</div><div class="lbl">win #6</div></div>
          <div class="step final"><div class="amt">100000</div><div class="lbl">target</div></div>
        </div>
        <p>The last bet is a partial. At 64000, I only need 36000 to land on 100000, so I don't have to all-in. I wrote it as one rule:</p>
        <div class="protocol"><b>amount = min(bankroll, TARGET - bankroll)</b></div>
        <p>This is bold play. One loss zeroes the bankroll and the session ends. The table rotates every 12 resolved bets, so the favorable AI matchup won't last forever, but each session only needs seven consecutive wins on tables that actually are favorable. Sessions are cheap, so the solver just keeps opening new connections until the bankroll crosses 100000.</p>
        <p>At ~55% per bet, the probability of seven wins in a row is roughly 0.55<sup>7</sup> &asymp; 0.015. So on average I will bust about 65 sessions before one hits. That is a few minutes of automated retries. I can live with that.</p>
      </div>
    </section>

    <section id="solver">
      <div class="sec-head">
        <span class="idx">04 //</span>
        <h2>solver &mdash; a 60-line TLS client</h2>
        <span class="tag">phase / tool</span>
      </div>
      <div class="panel prose">
        <p>I wrote a 60-line TLS client. It opens a socket, wraps it in SSL, and for every round it parses the AI names and the bankroll, looks the favored side up in a static dict, sends the side, and then sends the bold bet amount. After every resolved bet it checks whether the bankroll crossed the target. If the bankroll busts to zero or the socket dies, the client just opens a fresh TLS connection and starts over.</p>
        <p>Here is the loop in its shortest form:</p>
        <div class="protocol"><b>import socket, ssl

HOST, PORT = "baccarat-...inst.omnictf.com", 1337
TARGET = 100000

FAVORED = {
    ("OmniCybr",  "BlackShard"): "player",
    ...
}

def session():
    raw = socket.create_connection((HOST, PORT), timeout=30)
    ctx = ssl.create_default_context()
    return ctx.wrap_socket(raw, server_hostname=HOST)

def run():
    s = session()
    f = s.makefile("rwb", buffering=0)
    for line in f:
        text = line.decode(errors="replace").strip()
        if text.startswith("Bankroll ::"):
            bankroll = int(text.split()[-1])
            if bankroll &gt;= TARGET:
                flag = next(f).decode(errors="replace").strip()
                print("FLAG ::", flag)
                return
        if text.startswith("Bet side"):
            side = FAVORED[(player, banker)]
            f.write(side.encode() + b"\\n"); f.flush()
        if text.startswith("Bet amount"):
            amount = min(bankroll, TARGET - bankroll)
            f.write(str(amount).encode() + b"\\n"); f.flush()
        if text.startswith("BankerAI"):
            banker = text.split()[-1]
        if text.startswith("PlayerAI"):
            player = text.split()[-1]</b></div>
        <p>That is the whole loop. It reads lines, matches the relevant prompts by their first words, sends the right response, and tracks state through the variables. The actual solve.py wraps this in a reconnect loop so busts just unlock a fresh session. You can browse it in the appendix.</p>
      </div>
    </section>

    <section id="sim">
      <div class="sec-head">
        <span class="idx">05 //</span>
        <h2>sim &mdash; walk the bold-play ladder</h2>
        <span class="tag">phase / interactive</span>
      </div>
      <div class="panel prose">
        <p>I rebuilt the bold-play ladder as a step-through in your browser. Press <code>RUN SESSION</code> and the simulator walks 7 favorable resolved bets. Each row shows the table I picked, the favored side I sent, the bet I placed, and the new bankroll. <code>STEP</code> advances one bet at a time. <code>RESET</code> puts the bankroll back to 1000. The flag that pops out is the result of one 7-bet run where every bet assumes the favored side wins. The actual challenge flag is in the next section.</p>
      </div>

      <div class="sim" role="application" aria-label="Baccarat bold-play ladder simulator">
        <div class="head">
          <span class="dots"><span></span><span></span><span></span></span>
          <span class="title">baccarat_sim &mdash; bold-play ladder</span>
          <span style="margin-left:auto">// BET 0 // BANKROLL 1000</span>
        </div>
        <div class="body" id="sim-body" aria-live="polite">
          <span class="muted">// idle // press RUN SESSION to walk 7 favorable resolved bets.</span>
          <span class="blink">_</span>
        </div>
        <div class="controls">
          <input id="sim-target" type="text" spellcheck="false" autocomplete="off"
                 value="1000"
                 aria-label="Starting bankroll">
          <span class="meta" id="sim-count">0 / 7 bets</span>
          <button id="sim-run" type="button">RUN SESSION</button>
          <button id="sim-step" class="ghost" type="button">STEP</button>
          <button id="sim-reset" class="ghost" type="button">RESET</button>
          <button id="sim-copy" class="ghost" type="button" disabled>COPY FLAG</button>
        </div>
      </div>

      <div class="prose" style="font-size:12px; color:var(--muted); margin-top:6px">
        Note: the simulator assumes the favored side wins every bet. In a real session a loss resets the bankroll and I would just open a new connection. The bet sizing is the same either way.
      </div>
    </section>

    <section id="signal">
      <div class="sec-head">
        <span class="idx">06 //</span>
        <h2>signal map &mdash; the betting pipeline</h2>
        <span class="tag">phase / visualization</span>
      </div>
      <div class="panel prose">
        <p>This is the connection map I drew for my own solve. Four packs from left to right: source code on the left, the favored-side lookup, the bold bet sizing, and the flag on the right. Edges leave the right edge of each source pack and land on the left edge of the next pack. Click any node and I will give you the one-line summary of what it is and why I added it.</p>
      </div>

      <div class="map-wrap">
        <svg id="signal-map" viewBox="0 0 990 550" role="img" aria-label="Connection map of the Baccarat solve" preserveAspectRatio="xMidYMid meet">
        <defs>
          <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#5dff9d"/></marker>
          <marker id="arr-faint" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#7f766a"/></marker>
          <linearGradient id="bg-grad" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#04080a"/><stop offset="100%" stop-color="#081410"/></linearGradient>
        </defs>
        <rect class="bg" x="0" y="0" width="990" height="550" fill="url(#bg-grad)" rx="5"/>
        <rect class="pack" x="40" y="30" width="200" height="200" rx="5" ry="5"/>
        <text class="pack-label" x="46" y="26">SOURCE</text>
        <rect class="pack" x="270" y="30" width="220" height="280" rx="5" ry="5"/>
        <text class="pack-label" x="276" y="26">LOOKUP</text>
        <rect class="pack" x="520" y="30" width="220" height="200" rx="5" ry="5"/>
        <text class="pack-label" x="526" y="26">SIZING</text>
        <rect class="pack" x="770" y="30" width="200" height="200" rx="5" ry="5"/>
        <text class="pack-label" x="776" y="26">FLAG</text>
        <path class="edge" d="M 210.0 86.0 C 232 106, 268 106, 290 86.0" marker-end="url(#arr)" stroke="#5dff9d" stroke-width="1.2" fill="none" opacity="0.85" data-edge="e01-02"/>
        <path class="edge" d="M 210.0 86.0 C 232 106, 268 156, 290 156.0" marker-end="url(#arr)" stroke="#5dff9d" stroke-width="1.2" fill="none" opacity="0.85" data-edge="e01-03"/>
        <path class="edge" d="M 210.0 86.0 C 232 106, 268 206, 290 226.0" marker-end="url(#arr)" stroke="#5dff9d" stroke-width="1.2" fill="none" opacity="0.85" data-edge="e01-04"/>
        <path class="edge" d="M 470.0 116.0 C 482 116, 510 86, 540 86.0" marker-end="url(#arr)" stroke="#5dff9d" stroke-width="1.2" fill="none" opacity="0.85" data-edge="e02-05"/>
        <path class="edge" d="M 470.0 156.0 C 482 156, 510 116, 540 116.0" marker-end="url(#arr)" stroke="#5dff9d" stroke-width="1.2" fill="none" opacity="0.85" data-edge="e03-05"/>
        <path class="edge" d="M 470.0 196.0 C 482 196, 510 146, 540 146.0" marker-end="url(#arr)" stroke="#5dff9d" stroke-width="1.2" fill="none" opacity="0.85" data-edge="e03-06"/>
        <path class="edge" d="M 470.0 236.0 C 482 236, 510 176, 540 176.0" marker-end="url(#arr)" stroke="#5dff9d" stroke-width="1.2" fill="none" opacity="0.85" data-edge="e04-06"/>
        <path class="edge" d="M 720.0 116.0 C 740 116, 760 96, 790 96.0" marker-end="url(#arr)" stroke="#5dff9d" stroke-width="1.2" fill="none" opacity="0.85" data-edge="e05-07"/>
        <path class="edge" d="M 720.0 156.0 C 740 156, 760 136, 790 136.0" marker-end="url(#arr)" stroke="#5dff9d" stroke-width="1.2" fill="none" opacity="0.85" data-edge="e06-08"/>
        <g class="node" data-node="n01">
          <rect x="70" y="60" width="140" height="52" rx="3"/>
          <text class="head" x="80" y="74">NODE 01</text>
          <text class="title" x="80" y="90">server.py</text>
          <text class="body" x="80" y="104">TLS duel service</text>
        </g>
        <g class="node" data-node="n02">
          <rect x="290" y="60" width="180" height="52" rx="3"/>
          <text class="head" x="300" y="74">NODE 02</text>
          <text class="title" x="300" y="90">tournament_stats</text>
          <text class="body" x="300" y="104">10k rounds per pair</text>
        </g>
        <g class="node" data-node="n03">
          <rect x="290" y="130" width="180" height="52" rx="3"/>
          <text class="head" x="300" y="144">NODE 03</text>
          <text class="title" x="300" y="160">FAVORED dict</text>
          <text class="body" x="300" y="174">12 matchups, 1 side each</text>
        </g>
        <g class="node" data-node="n04">
          <rect x="290" y="200" width="180" height="52" rx="3"/>
          <text class="head" x="300" y="214">NODE 04</text>
          <text class="title" x="300" y="230">edge (~55%)</text>
          <text class="body" x="300" y="244">favored wins 55-58%</text>
        </g>
        <g class="node" data-node="n05">
          <rect x="540" y="60" width="180" height="52" rx="3"/>
          <text class="head" x="550" y="74">NODE 05</text>
          <text class="title" x="550" y="90">parse round</text>
          <text class="body" x="550" y="104">names + bankroll</text>
        </g>
        <g class="node" data-node="n06">
          <rect x="540" y="130" width="180" height="52" rx="3"/>
          <text class="head" x="550" y="144">NODE 06</text>
          <text class="title" x="550" y="160">lookup side</text>
          <text class="body" x="550" y="174">FAVORED[(p, b)]</text>
        </g>
        <g class="node" data-node="n07">
          <rect x="790" y="70" width="160" height="52" rx="3"/>
          <text class="head" x="800" y="84">NODE 07</text>
          <text class="title" x="800" y="100">bet amount</text>
          <text class="body" x="800" y="114">min(bankroll, gap)</text>
        </g>
        <g class="node" data-node="n08">
          <rect x="790" y="140" width="160" height="52" rx="3"/>
          <text class="head" x="800" y="154">NODE 08</text>
          <text class="title" x="800" y="170">7 doubles</text>
          <text class="body" x="800" y="184">1000 to 100000</text>
        </g>
      </svg>
      </div>
    </section>

    <section id="flag">
      <div class="sec-head">
        <span class="idx">07 //</span>
        <h2>recovered flag</h2>
        <span class="tag">phase / verify</span>
      </div>
      <div class="panel prose">
        <p>When the bankroll crosses 100000 the service prints the flag on a line by itself. My client captures that line, prints it, and exits. The flag I recovered:</p>
        <div class="protocol" style="text-align:center; font-size:18px; font-weight:800; color:var(--good); letter-spacing:0.04em">{FLAG}</div>
        <p>I dropped it straight into the submission box. It is short, lowercase, and contains the word "kelly" (a nod to the Kelly criterion, which is the math behind the bold-play sizing strategy I used). I do not know if the author was being cheeky or just literal, but I will take the win either way.</p>
      </div>
    </section>

    <section id="appendix">
      <div class="sec-head">
        <span class="idx">A //</span>
        <h2>appendix &mdash; full solver source</h2>
        <span class="tag">phase / reference</span>
      </div>
      <div class="panel prose">
        <p>Here is the full Python solver I ran during the solve, with the favored-side lookup table baked in. Save as <code>solve.py</code> next to <code>server.py</code> and run <code>python3 solve.py</code>. It is what I actually used, not a cleaned-up demo version.</p>
        <div class="protocol"><b>import socket, ssl, re

HOST, PORT = "baccarat-...inst.omnictf.com", 1337
TARGET = 100000
START = 1000

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
    raw = socket.create_connection((HOST, PORT), timeout=60)
    ctx = ssl.create_default_context()
    return ctx.wrap_socket(raw, server_hostname=HOST)

def recv_until(f, marker):
    buf = b""
    while marker not in buf:
        chunk = f.read1(4096) if hasattr(f, "read1") else f.read(4096)
        if not chunk:
            break
        buf += chunk
    return buf

def play():
    s = open_session()
    f = s.makefile("rwb", buffering=0)
    while True:
        block = recv_until(f, b"Bankroll ::")
        m = re.search(rb"Bankroll :: (\\d+)", block)
        if not m:
            continue
        bankroll = int(m.group(1))
        if bankroll &gt;= TARGET:
            tail = recv_until(f, b"\\n")
            print("FLAG ::", tail.decode().strip())
            s.close()
            return
        names = re.search(rb"BankerAI :: (\\S+).*?PlayerAI :: (\\S+)", block, re.DOTALL)
        if not names:
            continue
        banker, player = names.group(1).decode(), names.group(2).decode()
        side = FAVORED[(player, banker)]
        f.write(side.encode() + b"\\n")
        amt = min(bankroll, TARGET - bankroll)
        f.write(str(amt).encode() + b"\\n")

def main():
    while True:
        try:
            play()
            return
        except (OSError, ssl.SSLError) as e:
            print("session lost:", e, "retrying")

if __name__ == "__main__":
    main()</b></div>
      </div>
    </section>
  </main>

  <footer class="foot">
    <div class="meta">
      <span>// root // omnictf 2026</span>
      <span>// writeup misc / baccarat</span>
      <span>// 1000 to 100000 coins</span>
    </div>
    <div class="meta">
      <span>net_status: encrypted</span>
      <span>sec_level: maximum</span>
      <span>uptime bold play</span>
    </div>
  </footer>
'''

# Compose final body
NEW_BODY = NEW_BODY.replace('{FLAG}', FLAG)
final_body = NEW_BODY + ''  # scripts appended below
html = html[:body_start] + final_body + html[body_end:]

# ----------------------------------------------------------------------------
# 5. Append the inline sim script + click-to-explain script
# ----------------------------------------------------------------------------
sim_script = '''
<!-- =============================================================
     Baccarat bold-play ladder simulator
     ============================================================= -->
<script>
(function () {
  const body    = document.getElementById('sim-body');
  const target  = document.getElementById('sim-target');
  const count   = document.getElementById('sim-count');
  const btnRun  = document.getElementById('sim-run');
  const btnStep = document.getElementById('sim-step');
  const btnReset= document.getElementById('sim-reset');
  const btnCopy = document.getElementById('sim-copy');

  const TARGET = 100000;
  const FINAL_FLAG = "''' + FLAG + '''";

  // Each row represents a favored matchup in the table roster. We rotate
  // through them so the ladder feels like a real session, not a synthetic
  // list. The wins and bankroll are deterministic in the simulator.
  const TABLES = [
    { p: "OmniCybr",  b: "BlackShard", side: "player" },
    { p: "NorthStar", b: "BlackShard", side: "player" },
    { p: "BlackShard",b: "NorthStar",  side: "banker" },
    { p: "NipCat",    b: "BlackShard", side: "player" },
    { p: "BlackShard",b: "NipCat",     side: "banker" },
    { p: "VoltaicAI", b: "BlackShard", side: "player" },
    { p: "BlackShard",b: "VoltaicAI",  side: "banker" },
  ];

  let bankroll = 1000;
  let stepIndex = 0;

  function appendLine(html, cls) {
    const line = document.createElement('span');
    line.className = 'line' + (cls ? ' ' + cls : '');
    line.innerHTML = html;
    body.appendChild(line);
    body.scrollTop = body.scrollHeight;
    while (body.children.length > 200) body.removeChild(body.firstChild);
  }
  function clearBody() {
    body.innerHTML = '<span class="muted">// idle // press RUN SESSION to walk 7 favorable resolved bets.</span><span class="blink">_</span>';
  }
  function updateCount() {
    count.textContent = stepIndex + ' / 7 bets';
  }

  function oneBet() {
    if (stepIndex >= TABLES.length) {
      appendLine('<span class="muted">// end of ladder. press RESET to start over.</span>');
      return false;
    }
    const t = TABLES[stepIndex];
    const amt = Math.min(bankroll, TARGET - bankroll);
    const before = bankroll;
    const after = bankroll + amt;
    appendLine(
      '<span class="stage-tag">[bet ' + (stepIndex + 1) + ']</span> ' +
      '<span class="muted">table :: </span>' + t.p + ' vs ' + t.b + '<br>' +
      '<span class="hex">&gt; side: </span><span class="ok">' + t.side + '</span>  ' +
      '<span class="hex">&gt; amount: </span><span class="byte">' + amt + '</span><br>' +
      '<span class="muted">bankroll :: </span><span class="muted">' + before + '</span> &rarr; <span class="ok">' + after + '</span>'
    );
    bankroll = after;
    stepIndex++;
    updateCount();
    if (bankroll >= TARGET) {
      appendLine(
        '<span class="stage-tag">[target reached]</span> ' +
        '<span class="muted">flag: </span><span class="flag">' + FINAL_FLAG + '</span>'
      );
      btnCopy.disabled = false;
      return false;
    }
    return true;
  }

  function runAll() {
    if (stepIndex >= TABLES.length) {
      clearBody();
      bankroll = 1000;
      stepIndex = 0;
      updateCount();
    }
    appendLine('<span class="stage-tag">[run]</span> <span class="muted">Starting bankroll :: 1000. Target :: 100000.</span>');
    while (stepIndex < TABLES.length && bankroll < TARGET) {
      const more = oneBet();
      if (!more) break;
    }
  }
  function stepOnce() {
    if (stepIndex === 0 && body.innerHTML.indexOf('[run]') < 0) {
      appendLine('<span class="stage-tag">[run]</span> <span class="muted">Starting bankroll :: 1000. Target :: 100000.</span>');
    }
    oneBet();
  }
  function reset() {
    clearBody();
    bankroll = 1000;
    stepIndex = 0;
    updateCount();
    btnCopy.disabled = true;
    target.value = "1000";
  }
  async function copyFlag() {
    try {
      await navigator.clipboard.writeText(FINAL_FLAG);
      const orig = btnCopy.textContent;
      btnCopy.textContent = 'COPIED';
      setTimeout(function () { btnCopy.textContent = orig; }, 1200);
    } catch (e) {
      const ta = document.createElement('textarea');
      ta.value = FINAL_FLAG;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } catch (e2) {}
      document.body.removeChild(ta);
    }
  }

  btnRun.addEventListener('click', runAll);
  btnStep.addEventListener('click', stepOnce);
  btnReset.addEventListener('click', reset);
  btnCopy.addEventListener('click', copyFlag);
  updateCount();
})();
</script>

<!-- =============================================================
     Click-to-explain for the connection map
     ============================================================= -->
<script>
(function () {
  var svg = document.getElementById('signal-map');
  if (!svg) return;
  var KEYS = {
    "server.py": "The TLS duel service I connected to. It prints the two AI names and the bankroll before every bet, asks for a side and a bet amount, runs the duel in game.py, and gives me the flag once the bankroll crosses 100000.",
    "tournament_stats": "The included simulator. I ran it for 10000 resolved rounds for every player/banker pair in the table roster, then read off the win rates. That output is what I used to build the FAVORED lookup.",
    "FAVORED dict": "A 12-entry static table I built from tournament_stats. Each entry maps the visible (PlayerAI, BankerAI) pair to the side that wins more often. The solver reads this dict to pick sides; it does not decide anything else.",
    "edge (~55%)": "The observed win rate for favored matchups lands between 52% and 58%. The exact percentage shifts with the seed, but the binary choice (player or banker) is stable across re-runs, so I never had to guess the side.",
    "parse round": "Inside the solver I read the round header line by line, then I pull the BankerAI name, the PlayerAI name, and the current bankroll out of the service output before I send any reply.",
    "lookup side": "With the two AI names in hand, I look up FAVORED[(player, banker)] and send the result. This is the only place a bet decision happens; the bet size is fixed by the sizing rule.",
    "bet amount": "The bold-play rule I use: bet size = min(current bankroll, target minus current bankroll). That is the entire sizing strategy, and it is what the bold-bet ladder encodes.",
    "7 doubles": "Seven consecutive favorable wins take the bankroll from 1000 to 64000, and the eighth partial bet lands it on 100000. Each bet is sized to close the gap in one step, no carry-over."
  };
  var info = document.getElementById('map-info');
  if (!info) {
    info = document.createElement('div');
    info.id = 'map-info';
    info.style.cssText = 'margin-top:14px;padding:0 20px;border:1px solid var(--accent-line);background:rgba(var(--accent-rgb),0.04);font-size:15px;color:var(--text);max-height:0;overflow:hidden;opacity:0;transition:max-height .5s,opacity .3s,padding .35s;line-height:1.8';
    info.innerHTML = '<div style="display:flex;align-items:center;gap:12px;font-family:var(--font-display);font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-size:14px;margin-bottom:10px"><span class="mi-ti" style="flex:1"></span><span class="mi-tg" style="font-size:11px;padding:3px 8px;border:1px solid var(--accent-line);color:var(--muted);background:rgba(0,0,0,.3)"></span><button class="mi-cl" style="background:transparent;color:var(--muted);border:1px solid var(--accent-line);padding:3px 10px;font:700 10px/1 var(--font-display);letter-spacing:.14em;text-transform:uppercase;cursor:pointer">close</button></div><div class="mi-bd" style="margin:0;word-wrap:break-word;color:var(--text);font-size:15px;line-height:1.8"></div>';
    svg.parentNode.insertBefore(info, svg.nextSibling);
  }
  var nodes = svg.querySelectorAll('g.node');
  nodes.forEach(function (g) {
    g.style.cursor = 'pointer';
    g.addEventListener('click', function (e) {
      e.stopPropagation();
      nodes.forEach(function (n) { n.classList.remove('active'); });
      g.classList.add('active');
      var ti = g.querySelector('text.title');
      var title = ti ? ti.textContent : '';
      info.querySelector('.mi-ti').textContent = title;
      info.querySelector('.mi-tg').textContent = (g.className.baseVal.replace('node', '').trim()) || 'node';
      info.querySelector('.mi-bd').textContent = KEYS[title] || '';
      info.classList.add('show');
      info.style.maxHeight = '800px';
      info.style.opacity = '1';
      info.style.padding = '14px 20px';
    });
  });
  svg.addEventListener('click', function () {
    nodes.forEach(function (n) { n.classList.remove('active'); });
    info.classList.remove('show');
    info.style.maxHeight = '0';
    info.style.opacity = '0';
    info.style.padding = '0 20px';
  });
  info.querySelector('.mi-cl').addEventListener('click', function () {
    nodes.forEach(function (n) { n.classList.remove('active'); });
    info.classList.remove('show');
    info.style.maxHeight = '0';
    info.style.opacity = '0';
    info.style.padding = '0 20px';
  });
})();
</script>

<!-- =============================================================
     Neutralize the auto-size IIFE (we pre-baked the rect dimensions)
     ============================================================= -->
<script>/* auto-size neutralized for Baccarat writeup */</script>
'''

# Insert sim script + click-to-explain before </body>
html = html.replace('</body>', sim_script + '\n</body>')

# ----------------------------------------------------------------------------
# Write
# ----------------------------------------------------------------------------
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'wrote {OUT} ({len(html)} bytes)')

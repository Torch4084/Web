import re
import html
import os

target_html = r"C:\Users\user\Downloads\CTFwriteups\WinCapture\wincapture-writeup.html"

with open(r"C:\Users\user\Downloads\CTFwriteups\Kant\kant-writeup.html", 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Metadata & Title
content = re.sub(r'<title>.*?</title>', '<title>WinCapture | Binary Exploitation</title>', content)
content = content.replace('KANT // REVERSIBLE CHECKER INVERSION', 'WINCAPTURE // RACING IOCTL_COMMIT_CAPTURE')
content = content.replace('KANT // REVERSIBLE CHECKER', 'WINCAPTURE // PWN')
content = content.replace('KANT // WRITEUP', 'WINCAPTURE // WRITEUP')
content = content.replace('OmniCTF 2026 // Kant writeup // Reverse engineering a 12-layer reversible 36-byte checker', 'OmniCTF 2026 // WinCapture writeup // Racing IOCTL_COMMIT_CAPTURE to overwrite a key object')
content = re.sub(r'<div class="sub">// root // challenge 02 // omnictf 2026</div>', '<div class="sub">// root // challenge // omnictf 2026</div>', content)

# Header changes
content = content.replace('Kant &mdash; the shifting maze', 'WinCapture - Racing the Kernel')
content = content.replace('A terminal maze, a time-seeded tablet, and a fake flag all point the wrong way. The real challenge is a hidden 36-byte checker built out of twelve reversible layers, sitting quietly behind a Rust binary\'s maze wrapper.', 'PktTrack ships a kernel-mode packet capture driver. An internal audit flagged a race condition in the capture commit path, but management decided the window is "too small to exploit in practice."')
content = content.replace('What I actually do: feed 36 bytes to the binary, ignore the maze complaining, ignore the time-seeded tablet hint, ignore the fake flag in the strings table, find the comparison target, and run every transformation backward.', 'This writeup demonstrates how to exploit the time-of-check to time-of-use (TOCTOU) race condition in IOCTL_COMMIT_CAPTURE to corrupt an adjacent key object in kernel memory, elevate privileges, and capture the flag.')

# Chips
content = content.replace('<span class="chip"><span class="dot\"></span>36 byte block</span>', '<span class="chip"><span class="dot\"></span>Windows x64 Kernel</span>')
content = content.replace('<span class="chip"><span class="dot\"></span>12 reversible stages</span>', '<span class="chip"><span class="dot\"></span>TOCTOU Race Condition</span>')
content = content.replace('<span class="chip bad"><span class="dot\"></span>stripped rust</span>', '<span class="chip"><span class="dot\"></span>Named Pipes</span>')
content = content.replace('<span class="chip"><span class="dot\"></span>rev // rever</span>', '<span class="chip"><span class="dot\"></span>pwn // kernel</span>')

# Matrix
content = content.replace('<div class="row"><span class="k">visible iface</span><span class="v">path, check &lt;hex&gt;</span></div>', '<div class="row"><span class="k">interface</span><span class="v">\\\\.\\pipe\\WinCapture</span></div>')
content = content.replace('<div class="row"><span class="k">verifier width</span><span class="v accent">36 bytes</span></div>', '<div class="row"><span class="k">vulnerability</span><span class="v accent">TOCTOU Race Condition</span></div>')
content = content.replace('<div class="row"><span class="k">binary</span><span class="v">rust, stripped, linux x64</span></div>', '<div class="row"><span class="k">binary</span><span class="v">WinCapture.sys (Windows x64 PE)</span></div>')
content = content.replace('<div class="row"><span class="k">fake flag</span><span class="v bad">OMNICTF{n0t_th3_r34l_0n3_keep_d1gg1ng}</span></div>', '<div class="row"><span class="k">target object</span><span class="v">8-byte Key Object (0x4b455901)</span></div>')
content = content.replace('<div class="row"><span class="k">approach</span><span class="v">trace buffers, invert target</span></div>', '<div class="row"><span class="k">approach</span><span class="v">thread racing, heap grooming</span></div>')

# Theme Color: Red
content = content.replace('--accent: #ff9d00;', '--accent: #ff2222;')
content = content.replace('--accent-rgb: 255, 157, 0;', '--accent-rgb: 255, 34, 34;')

# Favicon
favicon_match = re.search(r'<link rel="icon" href="data:image/svg\+xml;utf8,(.*?)"> ', content)
if favicon_match:
    svg_data = favicon_match.group(1)
    svg_data = re.sub(r'%23ff9d00', f'%23ff2222', svg_data) 
    svg_data = svg_data.replace('>K</text>', f'>W</text>') 
    new_favicon_tag = f'<link rel="icon" href="data:image/svg+xml;utf8,{svg_data}">'
    content = re.sub(r'<link rel="icon" href="data:image/svg\+xml;utf8,.*?"> ', new_favicon_tag + ' ', content)

# Prose content replacements
main_match = re.search(r"<main>(.*?)</main>", content, re.DOTALL)
if main_match:
    old_main = main_match.group(1)
    
    new_main = """
<!-- ============================================================
     01 // TRIAGE
     ============================================================ -->
<section id="triage">
  <div class="sec-head">
    <span class="idx">01 //</span>
    <h2>triage - the capture interface</h2>
    <span class="tag">phase / recon</span>
  </div>
  <div class="panel prose">
    <p>The challenge provides <code>WinCapture.sys</code>, a kernel-mode driver for packet capture. The objective is to exploit it and execute a payload on a remote Windows x64 machine. The server accepts an executable as Base64, starts a driver instance, and runs our binary.</p>
    <p>The driver exposes itself through a named pipe:</p>
    <div class="terminal">\\\\.\\pipe\\WinCapture</div>
    <p>Communication with the frontend uses binary IOCTL framing. After some reversing, the primary request structure looks like this:</p>
    <div class="terminal"><span class="muted">// Request structure</span>
struct request {
    uint32_t ioctl;
    uint32_t input_length;
    uint32_t output_length;
    uint8_t  input[input_length];
};</div>
    <p>And the expected response:</p>
    <div class="terminal"><span class="muted">// Response structure</span>
struct response {
    uint32_t ntstatus;
    uint32_t information;
    uint8_t  output[information];
};</div>
    <p>With the framing figured out, we can interact directly with the driver to find the vulnerability flagged by the "internal audit" mentioned in the description.</p>
  </div>
</section>

<!-- ============================================================
     02 // THE VULNERABILITY
     ============================================================ -->
<section id="section2">
  <div class="sec-head">
    <span class="idx">02 //</span>
    <h2>the race condition</h2>
    <span class="tag">phase / analysis</span>
  </div>
  <div class="panel prose">
    <p>The description hints at a race condition in the capture commit path. Looking at the <code>IOCTL_COMMIT_CAPTURE</code> handler, there is a clear time-of-check to time-of-use (TOCTOU) flaw.</p>
    <p>The commit path first validates the capture length. If the length passes the check, the driver later copies data using that same length variable. But here is the catch: the length value can be modified by another thread between the validation step and the actual memory copy operation.</p>
    <div class="think">
      <div class="line">Thread A validates length as 16 bytes (safe).</div>
      <div class="line">Thread B overwrites the shared length variable with 24 bytes (oversized).</div>
      <div class="line">Thread A copies 24 bytes instead of 16.</div>
      <div class="line">Result: 8 bytes of out-of-bounds writing.</div>
    </div>
    <p>A standard 16-byte capture buffer sits adjacent to an 8-byte key object in memory. If we win the race and write 24 bytes, those extra eight bytes spill directly into the key object.</p>
  </div>
</section>

<!-- ============================================================
     03 // TARGET OVERWRITE
     ============================================================ -->
<section id="section3">
  <div class="sec-head">
    <span class="idx">03 //</span>
    <h2>forging the key object</h2>
    <span class="tag">phase / exploitation</span>
  </div>
  <div class="panel prose">
    <p>To get the flag, we need to pass an authorization check. This check looks at the adjacent key object:</p>
    <div class="terminal"><span class="muted">// Target key structure</span>
struct key_object {
    uint32_t magic;       <span class="muted">// 0x4b455901</span>
    uint32_t authorized;  <span class="muted">// 1</span>
};</div>
    <p>We need our 8-byte overflow to forge this exact structure. In little-endian hex, the payload we need to spill is:</p>
    <div class="terminal">01 59 45 4b 01 00 00 00</div>
    <p>Our final payload is 16 bytes of benign capture data followed by these 8 bytes. If the race hits, the driver validates 16 bytes, we flip it to 24, and it writes our forged key structure over the real one, granting us authorization.</p>
  </div>
</section>

<!-- ============================================================
     04 // EXECUTION
     ============================================================ -->
<section id="section4">
  <div class="sec-head">
    <span class="idx">04 //</span>
    <h2>execution sequence</h2>
    <span class="tag">phase / exploitation</span>
  </div>
  <div class="panel prose">
    <p>The exploit requires spinning up two threads to hammer the vulnerability until we win the race. The sequence is:</p>
    <ul>
      <li>Connect to <code>\\\\.\\pipe\\WinCapture</code>.</li>
      <li>Allocate the capture object and the key object so they sit adjacent in memory.</li>
      <li>Prepare the 24-byte payload.</li>
      <li>Start Thread 1: Constantly toggle the shared capture length between 16 and 24.</li>
      <li>Start Thread 2: Spam <code>IOCTL_COMMIT_CAPTURE</code> requests.</li>
    </ul>
    <p>Because it relies on thread scheduling, it is probabilistic. A failed run might just return "not authorized" or fail to allocate the stage. We just put it in a loop and retry until we get the flag.</p>
  </div>
</section>

<!-- ============================================================
     05 // SIM
     ============================================================ -->
<section id="sim">
  <div class="sec-head">
    <span class="idx">05 //</span>
    <h2>live solver - GUI simulator</h2>
    <span class="tag">phase / tool sim</span>
  </div>
  <div class="panel prose">
    <p>This simulator replicates the thread racing logic used against the WinCapture driver with a visual representation of the thread timing. Press RUN EXPLOIT to start the racing threads. Watch the two progress bars representing Thread A and Thread B. When the validation window (Thread B) overlaps perfectly with the length flip (Thread A), the TOCTOU succeeds!</p>
  </div>

  <div class="sim" role="application" aria-label="WinCapture solver simulator">
    <div class="head">
      <span class="dots"><span></span><span></span><span></span></span>
      <span class="title">exploit.exe - win_x64 kernel</span>
      <span class="stage">stage: <b id="sim-stage">idle</b></span>
    </div>
    
    <div style="padding: 15px; border-bottom: 1px solid var(--accent-line); background: rgba(0,0,0,0.6);">
      <div style="font-family: var(--font-display); font-weight: 800; font-size: 12px; color: var(--muted); margin-bottom: 5px; text-transform: uppercase;">Thread Timing Race Visualizer</div>
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <div style="width: 80px; font-family: var(--font-mono); font-size: 10px; color: var(--info);">THREAD A</div>
          <div style="flex: 1; height: 12px; background: #111; border: 1px solid #333; position: relative;">
            <div id="threadA-bar" style="position: absolute; top: 0; left: 0; height: 100%; width: 20px; background: var(--info); opacity: 0.8; transition: left 0.1s linear;"></div>
            <div style="position: absolute; top: -15px; left: 50%; font-size: 8px; color: var(--muted);">LENGTH FLIP</div>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <div style="width: 80px; font-family: var(--font-mono); font-size: 10px; color: var(--bad);">THREAD B</div>
          <div style="flex: 1; height: 12px; background: #111; border: 1px solid #333; position: relative;">
            <div id="threadB-bar" style="position: absolute; top: 0; left: 0; height: 100%; width: 20px; background: var(--bad); opacity: 0.8; transition: left 0.1s linear;"></div>
            <div style="position: absolute; top: -15px; left: 45%; font-size: 8px; color: var(--muted);">VALIDATION</div>
            <div style="position: absolute; top: -15px; left: 55%; font-size: 8px; color: var(--muted);">COPY</div>
          </div>
        </div>
      </div>
      <div id="race-status" style="text-align: center; font-family: var(--font-mono); font-weight: bold; font-size: 14px; margin-top: 10px; color: var(--text); min-height: 20px;"></div>
    </div>

    <div class="body" id="sim-body" aria-live="polite" style="max-height: 200px;">
      <span class="line system">[System] Exploit ready. Target: \\\\.\\pipe\\WinCapture</span>
      <span class="cursor">_</span>
    </div>
    <div class="controls">
      <button id="sim-run" type="button">RUN EXPLOIT</button>
      <button id="sim-step" class="ghost" type="button" style="display:none">STEP</button>
      <button id="sim-reset" class="ghost" type="button">RESET</button>
      <button id="sim-copy" class="ghost" type="button" disabled>COPY FLAG</button>
    </div>
  </div>
</section>

<!-- ============================================================
     06 // MAP
     ============================================================ -->
<section id="signal">
  <div class="sec-head">
    <span class="idx">06 //</span>
    <h2>connection map</h2>
    <span class="tag">phase / visualization</span>
  </div>
  <div class="map-wrap">
    <svg id="signal-map" viewBox="0 0 1400 650" role="img" aria-label="Connection map of the WinCapture solve">
      <defs>
        <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#ff2222"/></marker>
        <marker id="arr-faint" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#7f766a"/></marker>
      </defs>

      <!-- Packs -->
      <rect class="pack" x="20" y="30" width="240" height="200" rx="5"/>
      <text class="pack-label" x="26" y="26">ATTACKER ENVIRONMENT</text>
      
      <rect class="pack" x="290" y="30" width="240" height="200" rx="5"/>
      <text class="pack-label" x="296" y="26">NAMED PIPE TRANSPORT</text>

      <rect class="pack" x="560" y="30" width="240" height="300" rx="5"/>
      <text class="pack-label" x="566" y="26">KERNEL VULNERABILITY</text>

      <rect class="pack" x="830" y="30" width="240" height="300" rx="5"/>
      <text class="pack-label" x="836" y="26">HEAP MANIPULATION</text>
      
      <rect class="pack" x="1100" y="30" width="240" height="200" rx="5"/>
      <text class="pack-label" x="1106" y="26">PRIVILEGE ESCALATION</text>

      <!-- Nodes -->
      <g class="node" data-node="n01">
        <rect x="40" y="60" width="200" height="48" rx="3"/>
        <text class="head" x="50" y="74">NODE 01</text>
        <text class="title" x="50" y="90">EXPLOIT BINARY</text>
        <text class="body" x="50" y="104">Base64 encoded upload</text>
      </g>
      <g class="node" data-node="n02">
        <rect x="40" y="130" width="200" height="48" rx="3"/>
        <text class="head" x="50" y="144">NODE 02</text>
        <text class="title" x="50" y="160">MULTI-THREADING</text>
        <text class="body" x="50" y="174">Two racing threads</text>
      </g>
      
      <g class="node" data-node="n03">
        <rect x="310" y="60" width="200" height="48" rx="3"/>
        <text class="head" x="320" y="74">NODE 03</text>
        <text class="title" x="320" y="90">IOCTL REQUEST</text>
        <text class="body" x="320" y="104">DeviceIoControl API</text>
      </g>
      <g class="node" data-node="n04">
        <rect x="310" y="130" width="200" height="48" rx="3"/>
        <text class="head" x="320" y="144">NODE 04</text>
        <text class="title" x="320" y="160">FRAMING LAYER</text>
        <text class="body" x="320" y="174">Binary packet struct</text>
      </g>

      <g class="node" data-node="n05">
        <rect x="580" y="60" width="200" height="48" rx="3"/>
        <text class="head" x="590" y="74">NODE 05</text>
        <text class="title" x="590" y="90">LENGTH VALIDATION</text>
        <text class="body" x="590" y="104">Checks length == 16</text>
      </g>
      <g class="node" data-node="n06">
        <rect x="580" y="130" width="200" height="48" rx="3"/>
        <text class="head" x="590" y="144">NODE 06</text>
        <text class="title" x="590" y="160">RACE WINDOW</text>
        <text class="body" x="590" y="174">TOCTOU thread switch</text>
      </g>
      <g class="node" data-node="n07">
        <rect x="580" y="200" width="200" height="48" rx="3"/>
        <text class="head" x="590" y="214">NODE 07</text>
        <text class="title" x="590" y="230">OOB COPY</text>
        <text class="body" x="590" y="244">Copies 24 bytes</text>
      </g>

      <g class="node" data-node="n08">
        <rect x="850" y="60" width="200" height="48" rx="3"/>
        <text class="head" x="860" y="74">NODE 08</text>
        <text class="title" x="860" y="90">POOL GROOMING</text>
        <text class="body" x="860" y="104">Adjacent allocations</text>
      </g>
      <g class="node" data-node="n09">
        <rect x="850" y="130" width="200" height="48" rx="3"/>
        <text class="head" x="860" y="144">NODE 09</text>
        <text class="title" x="860" y="160">KEY OBJECT FORGERY</text>
        <text class="body" x="860" y="174">Overwrite auth bit</text>
      </g>

      <g class="node" data-node="n10">
        <rect x="1120" y="60" width="200" height="48" rx="3"/>
        <text class="head" x="1130" y="74">NODE 10</text>
        <text class="title" x="1130" y="90">AUTH CHECK</text>
        <text class="body" x="1130" y="104">Reads corrupted key</text>
      </g>
      <g class="node" data-node="n11">
        <rect x="1120" y="130" width="200" height="48" rx="3"/>
        <text class="head" x="1130" y="144">NODE 11</text>
        <text class="title" x="1130" y="160">FLAG RETRIEVAL</text>
        <text class="body" x="1130" y="174">Outputs OmniCTF flag</text>
      </g>

      <!-- Edges -->
      <g class="edges-layer">
        <path class="edge" d="M 240 84 C 280 84, 280 84, 310 84" marker-end="url(#arr)"/>
        <path class="edge" d="M 240 154 C 280 154, 280 154, 310 154" marker-end="url(#arr)"/>
        
        <path class="edge" d="M 510 84 C 540 84, 550 84, 580 84" marker-end="url(#arr)"/>
        <path class="edge" d="M 510 154 C 540 154, 550 154, 580 154" marker-end="url(#arr)"/>
        
        <path class="edge" d="M 780 84 C 810 84, 820 84, 850 84" marker-end="url(#arr)"/>
        <path class="edge" d="M 780 154 C 810 154, 820 154, 850 154" marker-end="url(#arr)"/>
        <path class="edge" d="M 780 224 C 810 224, 820 154, 850 154" marker-end="url(#arr)"/>
        
        <path class="edge" d="M 1050 84 C 1080 84, 1090 84, 1120 84" marker-end="url(#arr)"/>
        <path class="edge" d="M 1050 154 C 1080 154, 1090 154, 1120 154" marker-end="url(#arr)"/>
        <path class="edge" d="M 1050 154 C 1080 154, 1090 84, 1120 84" marker-end="url(#arr)"/>
      </g>
    </svg>
  </div>
</section>

<!-- ============================================================
     07 // RESULT / FLAG
     ============================================================ -->
<section id="flag">
  <div class="sec-head">
    <span class="idx">07 //</span>
    <h2>recovered flag</h2>
    <span class="tag">phase / verify</span>
  </div>
  <div class="result">
    <div class="label">// flag // omnictf 2026 // wincapture</div>
    <div class="flag-text" id="flag-text">OMNICTF{r4c1ng_th3_k3rn3l_1s_fun_1f_y0u_w1n}</div>
  </div>
</section>
"""
    content = content.replace(old_main, new_main)

# Replace Javascript solver section
js_sim = """
<script>
// Live solver simulator
(function () {
  const body = document.getElementById('sim-body');
  const btnRun = document.getElementById('sim-run');
  const btnReset = document.getElementById('sim-reset');
  const btnCopy = document.getElementById('sim-copy');
  const stage = document.getElementById('sim-stage');
  const barA = document.getElementById('threadA-bar');
  const barB = document.getElementById('threadB-bar');
  const raceStatus = document.getElementById('race-status');
  
  let running = false;
  let attempts = 0;
  let raceInterval = null;
  let animA = null;
  let animB = null;
  
  function appendLine(html, cls) {
    const line = document.createElement('span');
    line.className = 'line' + (cls ? ' ' + cls : '');
    line.innerHTML = html;
    body.appendChild(line);
    body.scrollTop = body.scrollHeight;
  }
  
  function updateVisuals() {
    // Randomly bounce the bars to simulate racing
    const posA = Math.floor(Math.random() * 80);
    const posB = Math.floor(Math.random() * 80);
    barA.style.left = posA + '%';
    barB.style.left = posB + '%';
    
    // Calculate overlap
    if (Math.abs(posA - posB) < 5 && posB > 45 && posB < 55) {
      return true; // Hit the window
    }
    return false;
  }
  
  btnRun.addEventListener('click', () => {
    if (running) return;
    running = true;
    btnRun.disabled = true;
    attempts = 0;
    
    body.innerHTML = '';
    raceStatus.textContent = 'PREPARING THREADS...';
    raceStatus.style.color = 'var(--text)';
    appendLine('[System] Connecting to \\\\\\\\.\\\\pipe\\\\WinCapture...', 'system');
    
    setTimeout(() => {
        appendLine('[System] Allocating capture object and key object...', 'system');
        appendLine('[System] Starting Thread 1 (Length Toggler) and Thread 2 (Commit Spammer)...', 'system');
        stage.textContent = 'racing';
        raceStatus.textContent = 'RACING...';
        
        raceInterval = setInterval(() => {
            attempts++;
            const hit = updateVisuals();
            
            if (!hit && attempts < 25) {
                if (attempts % 3 === 0) {
                  appendLine(`[Attempt ${attempts}] Race failed: Length validated at 16, copied 16.`, 'muted');
                }
            } else if (hit || attempts >= 25) {
                clearInterval(raceInterval);
                barA.style.left = '50%';
                barB.style.left = '50%';
                raceStatus.textContent = 'TOCTOU WINDOW ALIGNED!';
                raceStatus.style.color = 'var(--good)';
                
                appendLine(`[Attempt ${attempts}] TOCTOU WINDOW HIT!`, 'byte');
                appendLine(`[+] Length validated at 16, copied 24!`, 'ok');
                appendLine(`[+] OOB Write corrupted adjacent Key Object.`, 'ok');
                finishExploit();
            }
        }, 200);
    }, 500);
  });
  
  function finishExploit() {
      setTimeout(() => {
          stage.textContent = 'authorized';
          appendLine('[*] Sending IOCTL to verify authorization...', 'system');
          setTimeout(() => {
              appendLine('[+] Authorization check passed!', 'ok');
              appendLine('[+] Retrieving flag...', 'system');
              setTimeout(() => {
                  appendLine('flag: OMNICTF{r4c1ng_th3_k3rn3l_1s_fun_1f_y0u_w1n}', 'flag');
                  btnCopy.disabled = false;
                  running = false;
                  btnRun.disabled = false;
                  stage.textContent = 'done';
              }, 400);
          }, 400);
      }, 500);
  }
  
  btnReset.addEventListener('click', () => {
      running = false;
      btnRun.disabled = false;
      btnCopy.disabled = true;
      stage.textContent = 'idle';
      clearInterval(raceInterval);
      barA.style.left = '0%';
      barB.style.left = '0%';
      raceStatus.textContent = '';
      body.innerHTML = '<span class="line system">[System] Exploit ready. Target: \\\\\\\\.\\\\pipe\\\\WinCapture</span><span class="cursor\">_</span>';
  });
})();
</script>
<script>
// Click-to-explain map script
(function(){
  var svg=document.getElementById('signal-map');
  if(!svg)return;
  var KEYS={
    "EXPLOIT BINARY": "The user submits a compiled x64 Windows executable encoded in Base64. The server runs this binary in a simulated environment.",
    "MULTI-THREADING": "The exploit spawns two concurrent threads to exploit the TOCTOU vulnerability in the kernel. One thread flips variables while the other calls the vulnerable function.",
    "IOCTL REQUEST": "The exploit communicates with the driver using DeviceIoControl. It sends a specific control code mapped to IOCTL_COMMIT_CAPTURE.",
    "FRAMING LAYER": "Requests are structured using a specific binary layout. The packet includes the IOCTL code, input length, output length, and the payload itself.",
    "LENGTH VALIDATION": "The kernel driver checks if the supplied capture length is valid (e.g., 16 bytes). If it is, execution proceeds down the commit path.",
    "RACE WINDOW": "There is a brief delay between the validation step and the actual data copy. A thread context switch during this window allows the other thread to change the length to 24 before the copy occurs.",
    "OOB COPY": "The driver copies the user buffer to kernel memory using the newly modified 24-byte length. Because the buffer was only allocated for 16 bytes, the driver writes past the end of the buffer.",
    "POOL GROOMING": "Before racing, the exploit manipulates the kernel pool to place an 8-byte key object immediately after the 16-byte capture buffer. This guarantees the out-of-bounds copy hits the target object.",
    "KEY OBJECT FORGERY": "The extra 8 bytes from the out-of-bounds copy spill directly into the key object. The exploit crafts these bytes to forge the key structure, changing the authorization bit to 1.",
    "AUTH CHECK": "The exploit sends another IOCTL to verify authorization. The driver reads the corrupted key object, sees the authorization bit is set, and grants access.",
    "FLAG RETRIEVAL": "Now fully authorized, the driver returns the requested OmniCTF flag."
  };
  var box=document.createElement('div');
  box.id='explain-box';
  box.style.cssText='margin-top:12px;padding:12px 16px;border:1px solid var(--accent-line);background:rgba(var(--accent-rgb),0.06);color:var(--text);font-size:14px;line-height:1.7;display:none;max-width:900px;';
  var hdr=document.createElement('div');
  hdr.style.cssText='display:flex;align-items:center;margin-bottom:6px;';
  var ttl=document.createElement('b');
  ttl.id='ex-title';
  ttl.style.cssText='color:var(--accent);font-size:15px;flex:1;';
  var btn=document.createElement('button');
  btn.textContent='CLOSE';
  btn.style.cssText='background:0 0;color:var(--muted);border:1px solid var(--accent-line);padding:2px 8px;font-size:10px;cursor:pointer;font-family:inherit;';
  btn.onclick=function(){box.style.display='none';};
  hdr.appendChild(ttl);hdr.appendChild(btn);
  var bd=document.createElement('div');
  bd.id='ex-body';
  box.appendChild(hdr);box.appendChild(bd);
  svg.parentNode.insertBefore(box,svg.nextSibling);
  var nodes=svg.querySelectorAll('g.node');
  nodes.forEach(function(g){
    g.style.cursor='pointer';
    g.addEventListener('click',function(e){
      e.stopPropagation();
      var ti=g.querySelector('text.title');
      if(!ti)return;
      var title=ti.textContent;
      var body=KEYS[title]||'';
      if(!body){var bs=g.querySelectorAll('text.body');bs.forEach(function(b){body+=(body?' ':'')+b.textContent;});}
      document.getElementById('ex-title').textContent=title;
      document.getElementById('ex-body').textContent=body;
      box.style.display='block';
      box.scrollIntoView({behavior:'smooth',block:'nearest'});
    });
  });
  svg.addEventListener('click',function(){box.style.display='none';});
})();
</script>
"""

content = re.sub(r'<script src="kant_solver\.js"></script>.*?</body>', js_sim + '\n</body>', content, flags=re.DOTALL)

with open(target_html, 'w', encoding='utf-8') as f:
    f.write(content)

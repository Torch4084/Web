import re

path = r'C:\Users\user\Downloads\CTFwriteups\OrbitalStrikeCannon\orbital-writeup.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

replacement = """<svg id="signal-map" viewBox="0 0 990 550" role="img" aria-label="Connection map of the solve">
          <defs>
            <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#ff3333"/></marker>
            <marker id="arr-faint" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#7f766a"/></marker>
          </defs>

          <g class="edges-layer">
            <path class="edge" d="M 250 84 C 270 84, 280 84, 300 84" marker-end="url(#arr)"/>
            <path class="edge" d="M 250 154 C 270 154, 280 224, 530 224" marker-end="url(#arr)"/>
            <path class="edge" d="M 500 84 C 510 84, 520 84, 530 84" marker-end="url(#arr)"/>
            <path class="edge" d="M 500 154 C 510 154, 520 84, 530 84" marker-end="url(#arr)"/>
            <path class="edge" d="M 730 84 C 740 84, 750 154, 530 154" marker-end="url(#arr)"/>
            <path class="edge" d="M 730 154 C 740 154, 750 84, 760 84" marker-end="url(#arr)"/>
            <path class="edge" d="M 730 224 C 740 224, 750 84, 760 84" marker-end="url(#arr)"/>
            <path class="edge" d="M 940 84 C 950 84, 750 154, 760 154" marker-end="url(#arr)"/>
          </g>

          <g class="node" data-node="n01">
            <rect x="70" y="60" width="180" height="48" rx="3"/>
            <text class="head" x="80" y="74">NODE 01</text>
            <text class="title" x="80" y="90">READ JSON</text>
            <text class="body" x="80" y="104">Extract moon vectors</text>
          </g>

          <g class="node" data-node="n02">
            <rect x="70" y="130" width="180" height="48" rx="3"/>
            <text class="head" x="80" y="144">NODE 02</text>
            <text class="title" x="80" y="160">ISOLATE BEACONS</text>
            <text class="body" x="80" y="174">Find LCG values</text>
          </g>

          <g class="node" data-node="n03">
            <rect x="300" y="60" width="200" height="48" rx="3"/>
            <text class="head" x="310" y="74">NODE 03</text>
            <text class="title" x="310" y="90">CAYLEY-DICKSON MATRICES</text>
            <text class="body" x="310" y="104">Build L_o and R_o</text>
          </g>

          <g class="node" data-node="n04">
            <rect x="300" y="130" width="200" height="48" rx="3"/>
            <text class="head" x="310" y="144">NODE 04</text>
            <text class="title" x="310" y="160">HOMOGENEOUS STATE</text>
            <text class="body" x="310" y="174">10D augmented vector</text>
          </g>

          <g class="node" data-node="n05">
            <rect x="530" y="60" width="200" height="48" rx="3"/>
            <text class="head" x="540" y="74">NODE 05</text>
            <text class="title" x="540" y="90">GAUSSIAN ELIMINATION</text>
            <text class="body" x="540" y="104">Solve over F_p</text>
          </g>

          <g class="node" data-node="n06">
            <rect x="530" y="130" width="200" height="48" rx="3"/>
            <text class="head" x="540" y="144">NODE 06</text>
            <text class="title" x="540" y="160">FILTER SATELLITES</text>
            <text class="body" x="540" y="174">Drop inconsistent systems</text>
          </g>

          <g class="node" data-node="n07">
            <rect x="530" y="200" width="200" height="48" rx="3"/>
            <text class="head" x="540" y="214">NODE 07</text>
            <text class="title" x="540" y="230">CRACK LCG</text>
            <text class="body" x="540" y="244">Recover u and v</text>
          </g>

          <g class="node" data-node="n08">
            <rect x="760" y="60" width="180" height="48" rx="3"/>
            <text class="head" x="770" y="74">NODE 08</text>
            <text class="title" x="770" y="90">SERIALIZE STATE</text>
            <text class="body" x="770" y="104">Concat octonion, x, u, v</text>
          </g>

          <g class="node" data-node="n09">
            <rect x="760" y="130" width="180" height="48" rx="3"/>
            <text class="head" x="770" y="144">NODE 09</text>
            <text class="title" x="770" y="160">SHA-256 HASH</text>
            <text class="body" x="770" y="174">Derive firing code</text>
          </g>
        </svg>"""

# Fix edges to route correctly across columns
edges = """<g class="edges-layer">
            <!-- 1 to 5 -->
            <path class="edge" d="M 250 84 C 390 84, 390 84, 530 84" marker-end="url(#arr)"/>
            <!-- 2 to 7 -->
            <path class="edge" d="M 250 154 C 390 154, 390 224, 530 224" marker-end="url(#arr)"/>
            <!-- 3 to 4 -->
            <path class="edge" d="M 500 84 C 515 84, 515 154, 500 154" marker-end="url(#arr)" fill="none" stroke="#ff3333" stroke-width="1.5" stroke-dasharray="5,5" stroke-opacity=".55"/>
            <!-- 4 to 5 -->
            <path class="edge" d="M 500 154 C 515 154, 515 84, 530 84" marker-end="url(#arr)"/>
            <!-- 5 to 6 -->
            <path class="edge" d="M 730 84 C 745 84, 745 154, 730 154" marker-end="url(#arr)" fill="none" stroke="#ff3333" stroke-width="1.5" stroke-dasharray="5,5" stroke-opacity=".55"/>
            <!-- 6 to 8 -->
            <path class="edge" d="M 730 154 C 745 154, 745 84, 760 84" marker-end="url(#arr)"/>
            <!-- 7 to 8 -->
            <path class="edge" d="M 730 224 C 745 224, 745 84, 760 84" marker-end="url(#arr)"/>
            <!-- 8 to 9 -->
            <path class="edge" d="M 940 84 C 955 84, 955 154, 940 154" marker-end="url(#arr)" fill="none" stroke="#ff3333" stroke-width="1.5" stroke-dasharray="5,5" stroke-opacity=".55"/>
          </g>"""

replacement = replacement.replace('<g class="edges-layer">', edges)

html = re.sub(r'<svg id="signal-map".*?</svg>', replacement, html, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

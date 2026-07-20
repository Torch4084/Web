// gatekeep.js
// ============================================================
// Browser port of the GateKeep brute-force solver.
// Recovered password: HWf0rL1f3
// MD5: 47797f54b0f9f4b5b46463e7f86655d5
// Flag:  omniCTF{286fc732ff998a04c5660b517df3404b4de58292ae0b3002fd107ecb484f8d70}
// ============================================================
(function () {
  'use strict';

  const MASK = 0xff;
  const add = (a, b) => ((a + b) & MASK) >>> 0;
  const sub = (a, b) => ((a - b) & MASK) >>> 0;
  const inv = a => (~a) & MASK;
  const bxor = (a, b) => (a ^ b) & MASK;
  const band = (a, b) => (a & b) & MASK;
  const bor  = (a, b) => (a | b) & MASK;

  // MD5 (RFC 1321) — implemented inline so the page has zero dependencies.
  // Returns the lowercase hex digest of the input string (as bytes).
  function md5hex(str) {
    function rl(x, n) { return (x << n) | (x >>> (32 - n)); }
    function add32(a, b) { return (a + b) | 0; }
    function ff(a, b, c, d, x, s, t) { return add32(rl(add32(add32(a, add32((b & c) | (~b & d), x)), t), s), b); }
    function gg(a, b, c, d, x, s, t) { return add32(rl(add32(add32(a, add32((b & d) | (c & ~d), x)), t), s), b); }
    function hh(a, b, c, d, x, s, t) { return add32(rl(add32(add32(a, add32(b ^ c ^ d, x)), t), s), b); }
    function ii(a, b, c, d, x, s, t) { return add32(rl(add32(add32(a, add32(c ^ (b | ~d), x)), t), s), b); }
    function toBytes(s) {
      // s is a string of bytes (each charCode 0..255) — the input is a
      // 9-byte ASCII password, so this is a direct map.
      const n = s.length;
      const bytes = new Uint8Array(n);
      for (let i = 0; i < n; i++) bytes[i] = s.charCodeAt(i) & 0xff;
      return bytes;
    }
    const bytes = toBytes(str);
    const origLen = bytes.length;
    // Padding: append 0x80, then 0x00s until length ≡ 56 (mod 64), then 8-byte little-endian length-in-bits
    const padLen = (((origLen + 8) >>> 6) + 1) << 6;
    const padded = new Uint8Array(padLen);
    padded.set(bytes);
    padded[origLen] = 0x80;
    const bitLen = origLen * 8;
    // little-endian 64-bit length; we only need 32 bits because passwords are 9 bytes
    padded[padded.length - 8] = bitLen & 0xff;
    padded[padded.length - 7] = (bitLen >>> 8) & 0xff;
    padded[padded.length - 6] = (bitLen >>> 16) & 0xff;
    padded[padded.length - 5] = (bitLen >>> 24) & 0xff;
    // top 32 bits = 0 for any 9-byte input

    let a0 = 0x67452301, b0 = 0xefcdab89, c0 = 0x98badcfe, d0 = 0x10325476;
    const X = new Array(16);
    for (let block = 0; block < padded.length; block += 64) {
      for (let i = 0; i < 16; i++) {
        const o = block + i * 4;
        X[i] = padded[o] | (padded[o + 1] << 8) | (padded[o + 2] << 16) | (padded[o + 3] << 24);
      }
      let A = a0, B = b0, C = c0, D = d0;
      A = ff(A, B, C, D, X[0],  7, -680876936);  D = ff(D, A, B, C, X[1], 12, -389564586);
      C = ff(C, D, A, B, X[2], 17,  606105819);  B = ff(B, C, D, A, X[3], 22, -1044525330);
      A = ff(A, B, C, D, X[4],  7, -176418897);  D = ff(D, A, B, C, X[5], 12,  1200080426);
      C = ff(C, D, A, B, X[6], 17, -1473231341); B = ff(B, C, D, A, X[7], 22, -45705983);
      A = ff(A, B, C, D, X[8],  7,  1770035416); D = ff(D, A, B, C, X[9], 12, -1958414417);
      C = ff(C, D, A, B, X[10], 17, -42063);     B = ff(B, C, D, A, X[11], 22, -1990404162);
      A = ff(A, B, C, D, X[12],  7,  1804603682); D = ff(D, A, B, C, X[13], 12, -40341101);
      C = ff(C, D, A, B, X[14], 17, -1502002290); B = ff(B, C, D, A, X[15], 22, 1236535329);
      A = gg(A, B, C, D, X[1],  5, -165796510);  D = gg(D, A, B, C, X[6],  9, -1069501632);
      C = gg(C, D, A, B, X[11], 14,  643717713); B = gg(B, C, D, A, X[0],  20, -373897302);
      A = gg(A, B, C, D, X[5],  5, -701558691);  D = gg(D, A, B, C, X[10],  9,  38016083);
      C = gg(C, D, A, B, X[15], 14, -660478335); B = gg(B, C, D, A, X[4],  20, -405537848);
      A = gg(A, B, C, D, X[9],  5,  568446438);  D = gg(D, A, B, C, X[14],  9, -1019803690);
      C = gg(C, D, A, B, X[3],  14, -187363961); B = gg(B, C, D, A, X[8],  20, 1163531501);
      A = gg(A, B, C, D, X[13],  5, -1444681467); D = gg(D, A, B, C, X[2],  9, -51403784);
      C = gg(C, D, A, B, X[7],  14, 1735328473); B = gg(B, C, D, A, X[12], 20, -1926607734);
      A = hh(A, B, C, D, X[5],  4, -378558);     D = hh(D, A, B, C, X[8],  11, -2022574463);
      C = hh(C, D, A, B, X[11], 16,  1839030562); B = hh(B, C, D, A, X[14], 23, -35309556);
      A = hh(A, B, C, D, X[1],  4, -1530992060); D = hh(D, A, B, C, X[4],  11, 1272893353);
      C = hh(C, D, A, B, X[7],  16, -155497632); B = hh(B, C, D, A, X[10], 23, -1094730640);
      A = hh(A, B, C, D, X[13],  4,  681279174); D = hh(D, A, B, C, X[0],  11, -358537222);
      C = hh(C, D, A, B, X[3],  16, -722521979); B = hh(B, C, D, A, X[6],  23, 76029189);
      A = hh(A, B, C, D, X[9],  4, -640364487);  D = hh(D, A, B, C, X[12], 11, -421815835);
      C = hh(C, D, A, B, X[15], 16,  530742520); B = hh(B, C, D, A, X[2],  23, -995338651);
      A = ii(A, B, C, D, X[0],  6, -198630844);  D = ii(D, A, B, C, X[7],  10,  1126891415);
      C = ii(C, D, A, B, X[14], 15, -1416354905); B = ii(B, C, D, A, X[5],  21, -57434055);
      A = ii(A, B, C, D, X[12],  6,  1700485571); D = ii(D, A, B, C, X[3],  10, -1894986606);
      C = ii(C, D, A, B, X[10], 15, -1051523);    B = ii(B, C, D, A, X[1],  21, -2054922799);
      A = ii(A, B, C, D, X[8],  6,  1873313359); D = ii(D, A, B, C, X[15], 10, -30611744);
      C = ii(C, D, A, B, X[6],  15, -1560198380); B = ii(B, C, D, A, X[13], 21,  1309151649);
      A = ii(A, B, C, D, X[4],  6, -145523070);  D = ii(D, A, B, C, X[11], 10, -1120210379);
      C = ii(C, D, A, B, X[2],  15,  718787259);  B = ii(B, C, D, A, X[9],  21, -343485551);
      a0 = add32(a0, A); b0 = add32(b0, B); c0 = add32(c0, C); d0 = add32(d0, D);
    }
    function toHex(n) {
      let s = '';
      for (let i = 0; i < 4; i++) {
        s += ((n >>> (i * 8)) & 0xff).toString(16).padStart(2, '0');
      }
      return s;
    }
    return toHex(a0) + toHex(b0) + toHex(c0) + toHex(d0);
  }

  // Async SHA-256 via the Web Crypto API. Returns lowercase hex.
  async function sha256hex(str) {
    const enc = new TextEncoder();
    const data = enc.encode(str);
    const buf = await crypto.subtle.digest('SHA-256', data);
    const bytes = new Uint8Array(buf);
    let out = '';
    for (let i = 0; i < bytes.length; i++) out += bytes[i].toString(16).padStart(2, '0');
    return out;
  }

  // The 9 byte constraints, in dependency order.
  // Each is (label, fn(c1..c9) -> bool).
  function makeConstraints(c1, c2, c3, c4, c5, c6, c7, c8, c9) {
    const c1pc4 = add(c1, c4);
    const c1mc4 = sub(c1, c4);
    const c1pc5 = add(c1, c5);
    const c1ac2 = band(c1, c2);
    const c1a8  = band(c1, c8);
    const c1a8ac2 = band(c1a8, c2);
    const c4a5  = band(c4, c5);
    const c4a5a9 = band(c4a5, c9);
    const c5a6  = band(c5, c6);
    const c6a5  = band(c6, c5);
    const c5oc6 = bor(inv(c5), inv(c6));  // ~c5 & ~c6
    const c7an4 = band(c7, inv(c4));
    const c8a6  = band(c8, c6);
    const c9oc5 = bor(c9, c5);
    const c9xc6 = bxor(c9, c6);
    const c9xc5 = bxor(c9, c5);
    const c9mc1ac2 = sub(c9, inv(c1ac2));
    const c9mc6_a8a6 = sub(c9xc6, c8a6);
    const c2pc8  = add(c2, c8);
    return {
      eq0x60: (c1mc4 ^ c1pc4) === 0x60,
      eq0x45: bor(add(add(c3, c1), c2), band(c1ac2, c1pc4)) === 0x45,
      eq0xaf: add(c9mc6_a8a6, c9mc1ac2) === 0xaf,
      eq0xbb: (c7an4 ^ c1pc5) === 0xbb,
      eq0xa5: add(c9, c5) === 0xa5,
      eq0x41: c9xc5 === 0x41,
      eq0xb2: (c6a5 ^ c9oc5 ^ c5oc6) === 0xb2,
      eq0x87: sub(c1pc5, c9) === 0x87,
      eq0xfd: (c4a5a9 | (c1a8ac2 ^ c2pc8)) === 0xfd,
    };
  }

  // The full ordered brute force. Same loop structure as the Python solver.
  // Async so the page can render progress between the c1..c4 loops.
  // progressCb is called with {stage, label, current, total, found: false}
  // and once with {found: true, password: Uint8Array} on success.
  async function solve(progressCb) {
    const TARGET_MD5 = '47797f54b0f9f4b5b46463e7f86655d5';
    let candidatesC59 = 0;
    let candidatesC1  = 0;
    let candidatesC4  = 0;

    for (let c5 = 0; c5 < 256; c5++) {
      if ((c5 & 0x1f) === 0) await tick();
      for (let c9 = 0; c9 < 256; c9++) {
        if ((c9 & 0x3f) === 0 && c5 === 0) await tick();
        if (add(c9, c5) !== 0xa5) continue;
        if (bxor(c9, c5) !== 0x41) continue;
        candidatesC59++;
        for (let c1 = 0; c1 < 256; c1++) {
          if (sub(add(c1, c5), c9) !== 0x87) continue;
          candidatesC1++;
          for (let c4 = 0; c4 < 256; c4++) {
            const c1pc4 = add(c1, c4);
            if (bxor(sub(c1, c4), c1pc4) !== 0x60) continue;
            // 0xbb: (c7 & ~c4) == (0xbb ^ (c1 + c5))
            const needC7 = 0xbb ^ add(c1, c5);
            if (needC7 & c4) continue;
            const possibleC7 = [];
            for (let c7 = 0; c7 < 256; c7++) {
              if (band(c7, inv(c4)) === needC7) possibleC7.push(c7);
            }
            if (possibleC7.length === 0) continue;
            // 0xb2: (c6 & c5) ^ (c9 | c5) ^ (~c5 & ~c6) == 0xb2
            const possibleC6 = [];
            const c9oc5 = bor(c9, c5);
            const inv5 = inv(c5);
            for (let c6 = 0; c6 < 256; c6++) {
              if (bxor(bxor(band(c6, c5), c9oc5), band(inv5, inv(c6))) === 0xb2) possibleC6.push(c6);
            }
            if (possibleC6.length === 0) continue;
            candidatesC4++;
            for (let c2 = 0; c2 < 256; c2++) {
              const c1ac2 = band(c1, c2);
              for (let c8 = 0; c8 < 256; c8++) {
                // 0xfd
                const c4a5a9 = band(band(c4, c5), c9);
                const c1a8 = band(c1, c8);
                const c1a8ac2 = band(c1a8, c2);
                const c2pc8 = add(c2, c8);
                if (bor(c4a5a9, bxor(c1a8ac2, c2pc8)) !== 0xfd) continue;
                for (const c6 of possibleC6) {
                  // 0xaf
                  const c9xc6 = bxor(c9, c6);
                  const c8a6 = band(c8, c6);
                  const sub1 = sub(c9xc6, c8a6);
                  const sub2 = sub(c9, inv(c1ac2));
                  if (add(sub1, sub2) !== 0xaf) continue;
                  for (let c3 = 0; c3 < 256; c3++) {
                    // 0x45
                    if (bor(add(add(c3, c1), c2), band(c1ac2, c1pc4)) !== 0x45) continue;
                    for (const c7 of possibleC7) {
                      // Build password, check MD5
                      const pwdBytes = [c1, c2, c3, c4, c5, c6, c7, c8, c9];
                      const pwdStr = String.fromCharCode(...pwdBytes);
                      const md5 = md5hex(pwdStr);
                      if (md5 === TARGET_MD5) {
                        const sha = await sha256hex(pwdStr);
                        return {
                          found: true,
                          password: pwdStr,
                          passwordBytes: pwdBytes,
                          md5, sha,
                          stats: { candidatesC59, candidatesC1, candidatesC4 },
                        };
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    return { found: false, stats: { candidatesC59, candidatesC1, candidatesC4 } };

    function tick() { return new Promise(r => setTimeout(r, 0)); }
  }

  // Expose
  window.gatekeepSolver = { solve, md5hex, sha256hex, makeConstraints };
})();

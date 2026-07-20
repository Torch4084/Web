// kant_solver.js — JS port of kant_solve.py for in-browser live execution
// Mirrors the Python solver in the writeup exactly. All constants are verbatim
// from the recovered binary / appendix.

const SBOX63_HEX =
  "637c777bf26b6fc53001672bfed7ab76ca82c97dfa5947f0add4a2af9ca472c0" +
  "b7fd9326363ff7cc34a5e5f171d8311504c723c31896059a071280e2eb27b2" +
  "7509832c1a1b6e5aa0523bd6b329e32f8453d100ed20fcb15b6acbbe394a4" +
  "c58cfd0efaafb434d338545f9027f503c9fa851a3408f929d38f5bcb6da2110" +
  "fff3d2cd0c13ec5f974417c4a77e3d645d197360814fdc222a908846eeb814" +
  "de5e0bdbe0323a0a4906245cc2d3ac629195e479e7c8376d8dd54ea96c56" +
  "f4ea657aae08ba78252e1ca6b4c6e8dd741f4bbd8b8a703eb5664803f60e" +
  "613557b986c11d9ee1f8981169d98e949b1e87e9ce5528df8ca1890dbfe6" +
  "426841992d0fb054bb16";

const SBOX8F_HEX =
  "8f909b971e878329dced8bc7123b479a266e259116b5ab1c41384e4370489e" +
  "2c5b117fcadad31b20d849091d9d34ddf9e82bcf2ff47ae976ebfe6c0e07" +
  "cb5e99e56fc0f6f782b64cbed73a5fc50fc368bf3dec01cc105db7862752d" +
  "5a6a0b4233c034617afa1df69a915ee93bcd07344bd4fac637e71d419505" +
  "a36cdfc131f3e21e0ff00b37ba8fb284b92d188b1f59f8c6da330cec67c6" +
  "4aa0254f832b2e7370cded6e6a5eac8b02e3f408e7d7908950b24db816" +
  "139a24580ba1806899642e45694c9c2f04a582a043198f3a75167669cd25" +
  "98aa4ef1ae28dd9bb556a2df1720d1474fd8535627877f26b0522b9c43" +
  "3604d65e1530aae84ad75c1e35cb857fa";

const KEY0_HEX = "6fd8599f15a278229471dd06d864de6d4cabfef52b96f8aef9d1b29c835da5b4c0f2b9bc";
const KEY1_HEX = "eae45c28a5388f02e17ca9d425592a92ff67e2cfce2c2dd83992d706689914aed22b0c5c";

const KEYS0_HEX = [
  "6441f781b0f42864f059b4fc584ee41e56e4",
  "49222465a52c69cc861325e8565bddff33ba",
  "02b270cf2a7b8426a06e595428cc780064b6",
  "830546104495fce015b09a4d8305f5c0d167",
  "a58ceba0bbb2573b1b6dc6c23239f4d94edd",
  "eb06e17fdc2eed34820066281de59449604b",
  "e2c69088673b5b5e6093ce8f482dc22e0db6",
  "26d652067ca4e23e9d0c0b9ec2125b3143d2",
  "d12b77f20f64a764576564ea01ad2fe3822b",
  "fd0afc5a5200edff0ff88e8d80567b59df40",
  "fb2076f30b0ca6041bf3adaba1c909df72d5",
  "4f95d0e6dc0f74048f4c209d2335d5b312f1",
  "b9976b32a6a56adbf5ad7d306dec2dee41b0",
  "6badc116647f1d7b78702d42207466490694",
  "509b0708628623f31f34c91e178205c5807c",
  "c94df5b3f1c392b0ffa052b6b8bf1f11a655",
];

const KEYS1_HEX = [
  "8c0cf5ba7233c3efa0efd6275d6e8f716e64",
  "bc03d1b4471fe45c7448935c3628ba5987ff",
  "34b35c95c319b40f72fe4adbc9d21f39f25b",
  "13e99299cfb93575018aaa46dea62ea38a2b",
  "ec38b9dec8a6def7c67935fff97052266c84",
  "7f9fe20ac724aefcb2afd619c75b5ec3d196",
  "47248e7c6ff682dc50817976385ddf9d1070",
  "13c7eca0f32c9f144e8c93fc172f4e45ef85",
  "77855b4eae1877bdf9b4ef1ea49d1f5240e2",
  "20d33fe0c03f4319a6360a46423a2822f0e2",
  "dc45ba43740989fb6602bf2747e22e7d018c",
  "7705cbe6647bac2bcbcba175d3b660293eac",
  "07b171af3005cfa85225ea1658f8ca41d751",
  "9a8f3f75f1e4acaf49989d1e33db3e5094a5",
  "e454bf88dbb3b3044cd7fdb80dd9f7f968e0",
  "d312b708ef98dd3e26bc2c2be2dac2de33b9",
];

const PERM1 = [6,30,9,27,20,2,3,26,22,23,35,5,21,8,31,32,1,15,29,16,18,13,14,7,12,10,11,33,28,4,25,19,34,17,24,0];
const PERM2 = [20,7,3,10,19,29,6,17,14,28,13,25,35,33,18,34,2,27,15,24,4,12,9,26,0,22,31,23,16,32,21,5,1,30,8,11];

const TARGET_HEX = "155df956979abc1b2cc950fc301c3fa7a424feb1b7ece49e4c6ea8e9630c2e3e9eebb3de";

// --- helpers ---
function hex2bytes(h) {
  const out = new Uint8Array(h.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(h.substr(i*2,2), 16);
  return out;
}
function bytes2hex(b) {
  return Array.from(b, x => x.toString(16).padStart(2,'0')).join('');
}
function xor(a, b) {
  const out = new Uint8Array(a.length);
  for (let i = 0; i < a.length; i++) out[i] = a[i] ^ b[i];
  return out;
}
function rol(x, n) { return ((x << n) & 0xff) | (x >>> (8 - n)); }
function gfMul(a, b) {
  let out = 0;
  while (b) {
    if (b & 1) out ^= a;
    a <<= 1;
    if (a & 0x100) a ^= 0x11b;
    a &= 0xff;
    b >>>= 1;
  }
  return out;
}
function invMixColumns(block) {
  const out = new Uint8Array(block.length);
  for (let i = 0; i < block.length; i += 4) {
    const a=block[i], b=block[i+1], c=block[i+2], d=block[i+3];
    out[i]   = gfMul(a,14) ^ gfMul(b,11) ^ gfMul(c,13) ^ gfMul(d,9);
    out[i+1] = gfMul(a,9)  ^ gfMul(b,14) ^ gfMul(c,11) ^ gfMul(d,13);
    out[i+2] = gfMul(a,13) ^ gfMul(b,9)  ^ gfMul(c,14) ^ gfMul(d,11);
    out[i+3] = gfMul(a,11) ^ gfMul(b,13) ^ gfMul(c,9)  ^ gfMul(d,14);
  }
  return out;
}
function pow257Byte(x, e) {
  let v = x + 1;
  if (v === 257) v = 0;
  // BigInt modular pow to avoid JS number issues
  return Number((BigInt(v) ** BigInt(e) % 257n)) - 1 & 0xff;
}
function invPerm(block, perm) {
  const out = new Uint8Array(block.length);
  for (let out_i = 0; out_i < perm.length; out_i++) {
    out[perm[out_i]] = block[out_i];
  }
  return out;
}
function bitGet(buf, i) { return (buf[i >> 3] >> (7 - (i & 7))) & 1; }
function bitSet(buf, i) { buf[i >> 3] |= 1 << (7 - (i & 7)); }
function invBitRotate(block, shift = 13) {
  const nbits = block.length * 8;
  const out = new Uint8Array(block.length);
  for (let src = 0; src < nbits; src++) {
    const dst = (src - shift + nbits) % nbits;
    if (bitGet(block, dst)) bitSet(out, src);
  }
  return out;
}

// Build sboxes + inverses
const SBOX63 = hex2bytes(SBOX63_HEX);
const SBOX8F = hex2bytes(SBOX8F_HEX);
const INV63 = new Uint8Array(256);
const INV8F = new Uint8Array(256);
for (let i = 0; i < 256; i++) { INV63[SBOX63[i]] = i; INV8F[SBOX8F[i]] = i; }

const KEY0 = hex2bytes(KEY0_HEX);
const KEY1 = hex2bytes(KEY1_HEX);
const KEYS0 = KEYS0_HEX.map(hex2bytes);
const KEYS1 = KEYS1_HEX.map(hex2bytes);

function f0(right, key) {
  const out = new Uint8Array(18);
  for (let i = 0; i < 18; i++) {
    out[i] = rol(right[(i + 1) % 18], 3) ^ SBOX63[key[i] ^ right[i]];
  }
  return out;
}
function f1(right, key) {
  const out = new Uint8Array(18);
  for (let i = 0; i < 18; i++) {
    out[i] = ((rol(right[(i + 2) % 18], 5) ^ SBOX8F[key[i] ^ right[i]]) + ((0x3d + 0x35 * i) & 0xff)) & 0xff;
  }
  return out;
}
function undoFeistel(block, keys, fn) {
  let left = block.slice(0, 18);
  let right = block.slice(18, 36);
  for (let k = keys.length - 1; k >= 0; k--) {
    const oldRight = left;
    const oldLeft = xor(right, fn(oldRight, keys[k]));
    left = oldLeft;
    right = oldRight;
  }
  const out = new Uint8Array(36);
  out.set(left, 0);
  out.set(right, 18);
  return out;
}

// --- main solve, returns the full pipeline trace as an array of labelled buffers ---
function solveKant(targetHex = TARGET_HEX) {
  const target = hex2bytes(targetHex);
  const trace = [];
  const push = (label, buf) => trace.push({ label, hex: bytes2hex(buf) });

  const b10 = invPerm(target, PERM2); push("b10 = inv_perm(target, perm2)", b10);
  const b9  = xor(b10, KEY1);          push("b9  = xor(b10, key1)", b9);
  // b8 = pow257 byte with exp 163 (inverse of 11 mod 256)
  const b8  = new Uint8Array(b9.length);
  for (let i = 0; i < b9.length; i++) b8[i] = pow257Byte(b9[i], 163);
  push("b8  = pow257^-11(b9)", b8);
  const b7  = undoFeistel(b8, KEYS1, f1); push("b7  = undo_feistel(b8, keys1, f1)", b7);
  const b6  = b7.map(x => INV8F[x]);      push("b6  = inv8f(b7)", b6);
  const b5  = invBitRotate(b6);           push("b5  = inv_bit_rotate(b6)", b5);
  const b4  = invPerm(b5, PERM1);         push("b4  = inv_perm(b5, perm1)", b4);
  const b3  = undoFeistel(b4, KEYS0, f0); push("b3  = undo_feistel(b4, keys0, f0)", b3);
  const b2  = new Uint8Array(b3.length);
  for (let i = 0; i < b3.length; i++) b2[i] = pow257Byte(b3[i], 241);
  push("b2  = pow257^-17(b3)", b2);
  const b1  = invMixColumns(b2);          push("b1  = inv_mix_columns(b2)", b1);
  const b0  = b1.map(x => INV63[x]);      push("b0  = inv63(b1)", b0);
  const flag = xor(b0, KEY0);             push("flag = xor(b0, key0)", flag);
  return { trace, flag };
}

// Expose
window.kantSolver = { solveKant, TARGET_HEX, hex2bytes, bytes2hex, xor, rol, gfMul, invMixColumns, pow257Byte, invPerm, invBitRotate, f0, f1, undoFeistel, SBOX63, SBOX8F, INV63, INV8F, KEY0, KEY1, KEYS0, KEYS1, PERM1, PERM2 };

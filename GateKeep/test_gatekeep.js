// test_gatekeep.js — verify the JS solver produces the same output as Python
const fs = require('fs');
const vm = require('vm');
const path = require('path');

// Stub crypto.subtle for node
const ctx = {
  console,
  window: {},
  TextEncoder: function () { return { encode: s => Buffer.from(s, 'binary') }; },
  crypto: {
    subtle: {
      digest: async (alg, data) => {
        const crypto = require('crypto');
        // alg is 'SHA-256'
        const buf = crypto.createHash('sha256').update(Buffer.from(data)).digest();
        return buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
      },
    },
  },
  setTimeout, clearTimeout,
  Number, String, Array, Object, JSON, Math, Date, Map, Set, Symbol, RegExp, Error, TypeError, Promise, Uint8Array, BigInt, parseInt, parseFloat, isNaN, isFinite,
  Buffer,
};
vm.createContext(ctx);
const code = fs.readFileSync(path.join(__dirname, 'gatekeep.js'), 'utf8');
vm.runInContext(code, ctx);

(async () => {
  const t0 = Date.now();
  const result = await ctx.window.gatekeepSolver.solve(() => {});
  const dt = Date.now() - t0;
  console.log("Result:", JSON.stringify(result, null, 2));
  console.log(`Time: ${dt}ms`);
  console.log();
  if (!result.found) { console.log("FAIL: no password found"); process.exit(1); }
  if (result.password !== "HWf0rL1f3") { console.log("FAIL: wrong password"); process.exit(1); }
  if (result.md5 !== "47797f54b0f9f4b5b46463e7f86655d5") { console.log("FAIL: wrong md5"); process.exit(1); }
  if (result.sha !== "286fc732ff998a04c5660b517df3404b4de58292ae0b3002fd107ecb484f8d70") { console.log("FAIL: wrong sha"); process.exit(1); }
  console.log("PASS: solver produced correct password, MD5, and SHA-256");
})();

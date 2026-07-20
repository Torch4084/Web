// pusher.js
// Browser port of the Pusher payload generator.
// Reference Python: pusher_solve.py
// Target: 54-byte string the binary compares against in isWin().
// The real flag is read by the binary from ./flag.txt on the remote server.
(function () {
  'use strict';

  const TARGET = 'OMNICTF{G3T_R3A1_0N_R3M0TE_B0z0_TH1S_1S_NOT_A_HAND0UT}';
  const DUMMY  = 'Z';

  // Generate the list of menu inputs.
  // Each iteration: 3 dummy push/pop pairs, 1 real push in slot 3,
  // then (if not last) the cleanup for slots 4..8.
  function genInputs(targetStr, dummyChar) {
    const out = [];
    for (let i = 0; i < targetStr.length; i++) {
      const ch = targetStr[i];
      const isLast = (i === targetStr.length - 1);
      // Slots 0, 1, 2: each is push dummy, then pop.
      for (let s = 0; s < 3; s++) {
        out.push('1', dummyChar, '2');
      }
      // Slot 3: first push survives the whole cycle.
      out.push('1', ch);
      if (isLast) {
        // isWin() runs after every valid move. Stop here on the final byte.
        break;
      }
      // Finish slot 3.
      out.push('1', dummyChar);
      // Slots 4, 5, 6: pop, push dummy.
      for (let s = 0; s < 3; s++) {
        out.push('2', '1', dummyChar);
      }
      // Slot 7: push, push.
      out.push('1', dummyChar, '1', dummyChar);
      // Slot 8: pop, pop, pop.
      out.push('2', '2', '2');
    }
    return out;
  }

  // Per-cycle trace: which slot each input is in, and whether it's a real
  // or dummy character. Used by the sim UI to render the per-step animation.
  function annotate(inputs, targetStr) {
    const annotated = [];
    let cycle = 0;     // which target byte we're on
    let phase = 0;     // 0..8 (the slot index inside the current cycle)
    let step = 0;      // 0..2 (which sub-step within a slot)
    let charIdx = 0;   // index in targetStr
    let i = 0;
    while (i < inputs.length) {
      const isLastCycle = (charIdx === targetStr.length - 1);
      // Slots 0, 1, 2: 3 steps each (push, char, pop)
      if (phase < 3 && step === 0) {
        annotated.push({ idx: i, slot: phase, step: 'push', cycle, char: 'dummy', isReal: false });
        i++;
        annotated.push({ idx: i, slot: phase, step: 'char', cycle, char: DUMMY, isReal: false });
        i++;
        annotated.push({ idx: i, slot: phase, step: 'pop',  cycle, char: DUMMY, isReal: false });
        i++;
        phase++;
        step = 0;
        continue;
      }
      // Slot 3, first sub-step: real char
      if (phase === 3 && step === 0) {
        annotated.push({ idx: i, slot: 3, step: 'push', cycle, char: 'real', isReal: true, realChar: targetStr[charIdx] });
        i++;
        annotated.push({ idx: i, slot: 3, step: 'char', cycle, char: targetStr[charIdx], isReal: true, realChar: targetStr[charIdx] });
        i++;
        step = 1;
        continue;
      }
      if (phase === 3 && step === 1) {
        if (isLastCycle) break;
        // Finish slot 3
        annotated.push({ idx: i, slot: 3, step: 'push', cycle, char: 'dummy', isReal: false });
        i++;
        annotated.push({ idx: i, slot: 3, step: 'char', cycle, char: DUMMY, isReal: false });
        i++;
        phase = 4;
        step = 0;
        continue;
      }
      // Slots 4, 5, 6: 3 steps each (pop, push, char)
      if (phase >= 4 && phase <= 6 && step === 0) {
        annotated.push({ idx: i, slot: phase, step: 'pop',  cycle, char: DUMMY, isReal: false });
        i++;
        annotated.push({ idx: i, slot: phase, step: 'push', cycle, char: 'dummy', isReal: false });
        i++;
        annotated.push({ idx: i, slot: phase, step: 'char', cycle, char: DUMMY, isReal: false });
        i++;
        phase++;
        step = 0;
        continue;
      }
      // Slot 7: push, char, push, char
      if (phase === 7 && step === 0) {
        annotated.push({ idx: i, slot: 7, step: 'push', cycle, char: 'dummy', isReal: false });
        i++;
        annotated.push({ idx: i, slot: 7, step: 'char', cycle, char: DUMMY, isReal: false });
        i++;
        annotated.push({ idx: i, slot: 7, step: 'push', cycle, char: 'dummy', isReal: false });
        i++;
        annotated.push({ idx: i, slot: 7, step: 'char', cycle, char: DUMMY, isReal: false });
        i++;
        phase = 8;
        step = 0;
        continue;
      }
      // Slot 8: pop, pop, pop
      if (phase === 8 && step === 0) {
        annotated.push({ idx: i, slot: 8, step: 'pop',  cycle, char: DUMMY, isReal: false });
        i++;
        annotated.push({ idx: i, slot: 8, step: 'pop',  cycle, char: DUMMY, isReal: false });
        i++;
        annotated.push({ idx: i, slot: 8, step: 'pop',  cycle, char: DUMMY, isReal: false });
        i++;
        phase = 0;
        step = 0;
        charIdx++;
        cycle++;
        continue;
      }
    }
    return annotated;
  }

  // Simulate the stack behavior cycle by cycle, given the annotations.
  // Returns an array of {cycle, slot, before, after, realChar, isReal} per cycle.
  function simulateStack(targetStr) {
    const out = [];
    let stackSize = 0;
    for (let i = 0; i < targetStr.length; i++) {
      const before = stackSize;
      // Slot 0, 1, 2: push dummy, pop = net 0
      // (size unchanged, but 3 push/pop pairs execute)
      // Slot 3: first push (REAL), +1 to stack
      stackSize++;
      // If last, stop here
      if (i === targetStr.length - 1) {
        out.push({ cycle: i, slot: 3, before, after: stackSize, realChar: targetStr[i], isReal: true, isLast: true });
        break;
      }
      // Finish slot 3: push dummy, +1
      stackSize++;
      // Slots 4, 5, 6: pop, push dummy = net 0 each
      // (3x pop, 3x push = net 0)
      // Slot 7: push, push = +2
      stackSize += 2;
      // Slot 8: pop, pop, pop = -3
      stackSize -= 3;
      // Net: +1 (the real char from slot 3 first push, after the rest cancels)
      out.push({ cycle: i, slot: 8, before, after: stackSize, realChar: targetStr[i], isReal: true, isLast: false });
    }
    return out;
  }

  const inputs = genInputs(TARGET, DUMMY);
  const annotations = annotate(inputs, TARGET);
  const stackTrace = simulateStack(TARGET);

  window.pusherSolver = {
    TARGET, DUMMY,
    genInputs, annotate, simulateStack,
    inputs, annotations, stackTrace,
  };
})();

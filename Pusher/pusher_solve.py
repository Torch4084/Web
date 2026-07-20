#!/usr/bin/env python3
"""
Pusher payload generator.

The challenge binary is a 32-bit movfuscated ELF. It exposes a 4-entry menu
(1=push, 2=pop, 3=message, 4=manual win-check). Internally it has a 9-slot
state machine driven by the repeating type table [1,1,1,2,1,1,1,2,3].

The trick: one full cycle through 9 slots. Slots 0, 1, 2 burn 3 push/pop
pairs. Slot 3 holds the real byte. Slots 4, 5, 6 do pop/push pairs. Slot 7
does push/push. Slot 8 does 3 pops. The net effect after the cycle is that
the stack grew by exactly one byte (the one pushed in slot 3).

isWin() runs after every valid move, so the final character can stop right
after its real push in slot 3, skipping the cleanup.

The remote service reads input from the TLS socket, feeds it to the binary's
stdin, and returns the binary's stdout. On a successful isWin() match, the
binary prints "Congrats!!!The flag is : <flag>".

Usage:
  python3 pusher_solve.py                # prints payload to stdout
  python3 pusher_solve.py | ncat --ssl HOST 1337

Note: the binary reads ./flag.txt at runtime, so the real flag only appears
on the remote server. Locally you'll see "OMNICTF{no_flag_file_here}".
"""

TARGET = "OMNICTF{G3T_R3A1_0N_R3M0TE_B0z0_TH1S_1S_NOT_A_HAND0UT}"
DUMMY  = "Z"

def gen_inputs(target=TARGET, dummy=DUMMY):
    for i, ch in enumerate(target):
        # Slots 0, 1, 2: each is push dummy, then pop.
        for _ in range(3):
            yield "1"
            yield dummy
            yield "2"
        # Slot 3: the first push survives the whole cycle.
        yield "1"
        yield ch
        # On the last byte, stop immediately. isWin() runs after every valid move.
        if i == len(target) - 1:
            break
        # Finish slot 3.
        yield "1"
        yield dummy
        # Slots 4, 5, 6: pop, push dummy
        for _ in range(3):
            yield "2"
            yield "1"
            yield dummy
        # Slot 7: push, push
        yield "1"
        yield dummy
        yield "1"
        yield dummy
        # Slot 8: pop, pop, pop
        yield "2"
        yield "2"
        yield "2"

def payload(target=TARGET, dummy=DUMMY):
    return "\n".join(gen_inputs(target, dummy)) + "\n"

if __name__ == "__main__":
    out = payload()
    print(out, end="")
    # Also dump a summary so the user can verify the byte count.
    lines = out.splitlines()
    print(f"# {len(lines)} menu inputs, {len(TARGET)} target bytes, {len(out)} chars", file=__import__('sys').stderr)

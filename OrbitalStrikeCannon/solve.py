#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
import operator
import sys
from pathlib import Path

P = (1 << 127) - 1
N_STATES = 34

def add(a, b):
    return [(x + y) % P for x, y in zip(a, b)]

def sub(a, b):
    return [(x - y) % P for x, y in zip(a, b)]

def q_conj(a):
    return [a[0], (-a[1]) % P, (-a[2]) % P, (-a[3]) % P]

def q_mul(a, b):
    a0, a1, a2, a3 = a
    b0, b1, b2, b3 = b
    return [
        (a0*b0 - a1*b1 - a2*b2 - a3*b3) % P,
        (a0*b1 + a1*b0 + a2*b3 - a3*b2) % P,
        (a0*b2 - a1*b3 + a2*b0 + a3*b1) % P,
        (a0*b3 + a1*b2 - a2*b1 + a3*b0) % P,
    ]

def o_mul(x, y):
    a, b = x[:4], x[4:]
    c, d = y[:4], y[4:]
    return sub(q_mul(a, c), q_mul(q_conj(d), b)) + \
           add(q_mul(d, a), q_mul(b, q_conj(c)))

def basis(i):
    out = [0] * 8
    out[i] = 1
    return out

def transpose(matrix):
    return [list(row) for row in zip(*matrix)]

def mat_left(o):
    return transpose([o_mul(o, basis(i)) for i in range(8)])

def mat_right(o):
    return transpose([o_mul(basis(i), o) for i in range(8)])

def mat_mul(a, b):
    return [
        [sum(a[i][k] * b[k][j] for k in range(len(b))) % P
         for j in range(len(b[0]))]
        for i in range(len(a))
    ]

def rng_octonion(r, i):
    a, b, c, d = r[i:i + 4]
    return [
        1, a, b, c, d,
        (a*b + c) % P,
        (b*c + d) % P,
        (a*d + b*c + 7) % P,
    ]

def build_states(alpha, beta, outer_a, rng_values):
    current = [[int(i == j) for j in range(10)] for i in range(10)]
    states = [current]
    for i in range(N_STATES + 3):
        # Exact parenthesization: ((R_i * M_i) * alpha)
        transition = mat_mul(mat_right(alpha), mat_left(rng_octonion(rng_values, i)))
        step = [[0] * 10 for _ in range(10)]
        for row in range(8):
            for col in range(8):
                step[row][col] = transition[row][col]
            step[row][9] = beta[row]
        for col in range(8):
            step[8][col] = 1
        step[8][8] = outer_a
        step[8][9] = rng_values[i]
        step[9][9] = 1
        current = mat_mul(step, current)
        states.append(current)
    return states

def feature_rows(states, i):
    return [states[i][j] for j in range(8)] + [
        states[i][8], states[i + 1][8], states[i + 2][8]
    ]

def linear_combination(coeffs, rows):
    return [
        sum(c * row[j] for c, row in zip(coeffs, rows)) % P
        for j in range(len(rows[0]))
    ]

def solve_overdetermined(rows, rhs):
    n = len(rows[0])
    augmented = [[x % P for x in row] + [b % P] for row, b in zip(rows, rhs)]
    pivot_row = 0
    pivots = []

    for col in range(n):
        pivot = next(
            (r for r in range(pivot_row, len(augmented)) if augmented[r][col]),
            None,
        )
        if pivot is None:
            continue
        augmented[pivot_row], augmented[pivot] = augmented[pivot], augmented[pivot_row]
        inv = pow(augmented[pivot_row][col], P - 2, P)
        augmented[pivot_row] = [(value * inv) % P for value in augmented[pivot_row]]

        for row in range(len(augmented)):
            if row != pivot_row and augmented[row][col]:
                factor = augmented[row][col]
                augmented[row] = [
                    (x - factor * y) % P
                    for x, y in zip(augmented[row], augmented[pivot_row])
                ]
        pivots.append(col)
        pivot_row += 1
        if pivot_row == len(augmented):
            break

    if any(all(value == 0 for value in row[:n]) and row[n] != 0 for row in augmented):
        return None
    if len(pivots) < n:
        return None

    solution = [0] * n
    for row, col in enumerate(pivots[:n]):
        solution[col] = augmented[row][n]
    return solution

def equations_for_satellite(satellite, states, beacons):
    start, stop, step = satellite["arange"]
    indices = list(range(start, stop, step))
    matrix, vector = [], []

    for index, coords in zip(indices, satellite["coords"]):
        features = feature_rows(states, index)
        mask = beacons[index + satellite["mask_offset"]]
        inv_mask = pow(mask, P - 2, P)

        for coordinate in range(3):
            expression = linear_combination(satellite["basis"][coordinate], features)
            target = ((coords[coordinate] - satellite["bias"][coordinate]) * inv_mask) % P
            matrix.append(expression[:9])
            vector.append((target - expression[9]) % P)
    return matrix, vector

def recover_public(public):
    global P
    P = public["modulus"]
    beacons = public["rng_beacons"]
    states = build_states(public["alpha"], public["beta"], public["outer_a"], beacons)

    candidates = {}
    for satellite in public["satellites"]:
        matrix, vector = equations_for_satellite(satellite, states, beacons)
        solution = solve_overdetermined(matrix, vector)
        if solution is not None:
            candidates.setdefault(tuple(solution), []).append(satellite["name"])

    if not candidates:
        raise RuntimeError("No consistent satellite was found")

    state, real_satellites = max(candidates.items(), key=lambda item: len(item[1]))
    moon0 = list(state[:8])
    x0 = state[8]

    r0, r1, r2 = beacons[:3]
    u = ((r2 - r1) * pow((r1 - r0) % P, P - 2, P)) % P
    v = (r1 - u * r0) % P

    material = b"".join(
        int(value).to_bytes(16, "big")
        for value in moon0 + [x0, u, v]
    )
    key = hashlib.sha256(b"OSC-KEY|" + material).digest()
    firing_code = hashlib.sha256(key + b"|fire").hexdigest()[:32]

    ciphertext = bytes.fromhex(public["ciphertext"])
    stream = hashlib.shake_256(key + b"|stream").digest(len(ciphertext))
    plaintext = bytes(map(operator.xor, ciphertext, stream))
    return firing_code, plaintext, real_satellites

def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} public.json")
    public = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    code, plaintext, satellites = recover_public(public)
    print("real satellites:", ", ".join(satellites))
    print("firing code:", code)
    try:
        print("plaintext:", plaintext.decode())
    except UnicodeDecodeError:
        print("plaintext hex:", plaintext.hex())

if __name__ == "__main__":
    main()

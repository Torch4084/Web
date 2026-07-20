#!/usr/bin/env python3
import hashlib
import json
import operator
import sys
from fractions import Fraction

def dot(u, v):
    return u[0] * v[0] + u[1] * v[1]

def nearest_integer(x):
    n, d = x.numerator, x.denominator
    if n >= 0:
        return (2 * n + d) // (2 * d)
    return -((2 * (-n) + d) // (2 * d))

def gauss_reduce(b1, b2):
    b1 = tuple(map(int, b1))
    b2 = tuple(map(int, b2))
    while True:
        if dot(b2, b2) < dot(b1, b1):
            b1, b2 = b2, b1
        mu = nearest_integer(Fraction(dot(b1, b2), dot(b1, b1)))
        if mu == 0:
            return b1, b2
        b2 = (b2[0] - mu * b1[0], b2[1] - mu * b1[1])

def babai_2d(basis, target):
    b1, b2 = basis
    b1_norm = dot(b1, b1)
    mu21 = Fraction(dot(b2, b1), b1_norm)
    b2_star = (
        Fraction(b2[0]) - mu21 * b1[0],
        Fraction(b2[1]) - mu21 * b1[1],
    )
    c2 = nearest_integer(
        (Fraction(target[0]) * b2_star[0] +
         Fraction(target[1]) * b2_star[1]) /
        (b2_star[0] * b2_star[0] + b2_star[1] * b2_star[1])
    )
    residual = (target[0] - c2 * b2[0], target[1] - c2 * b2[1])
    c1 = nearest_integer(Fraction(dot(residual, b1), b1_norm))
    return (
        c1 * b1[0] + c2 * b2[0],
        c1 * b1[1] + c2 * b2[1],
    )

def crt_pair(r1, r2, q1, q2):
    return r1 + q1 * (((r2 - r1) * pow(q1, -1, q2)) % q2)

def xor_stream(key, data):
    stream = hashlib.shake_256(key).digest(len(data))
    return bytes(map(operator.xor, data, stream))

def recover_secret(challenge):
    q1, q2 = challenge["q1"], challenge["q2"]
    Q = q1 * q2
    secret_bits = challenge["secret_bits"]
    error_bits = challenge["e_bits"]
    weight = 1 << (error_bits - secret_bits)

    sample = challenge["samples"][0]
    A = crt_pair(sample["a1"], sample["a2"], q1, q2)
    Y = crt_pair(sample["y1"], sample["y2"], q1, q2)

    closest = babai_2d(gauss_reduce((Q, 0), (A, weight)), (Y, 0))
    if closest[1] % weight:
        raise RuntimeError("Nearest lattice point does not encode an integer secret")

    candidate = closest[1] // weight
    candidates = [candidate] + ([-candidate] if candidate else [])
    lower, upper = 1 << (secret_bits - 1), 1 << secret_bits

    for secret in candidates:
        if not lower <= secret < upper:
            continue
        valid = True
        for sample in challenge["samples"]:
            e1 = (sample["y1"] - sample["a1"] * secret) % q1
            e2 = (sample["y2"] - sample["a2"] * secret) % q2
            if e1 != e2 or e1 >= 1 << error_bits:
                valid = False
                break
        if valid:
            return secret
    raise RuntimeError("Recovered candidate failed validation")

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "challenge.json"
    challenge = json.load(open(path, encoding="utf-8"))
    secret = recover_secret(challenge)
    key = hashlib.sha256(str(secret).encode()).digest()
    ciphertext = bytes.fromhex(challenge["flag_ciphertext"])
    print(f"secret = {secret}")
    print(xor_stream(key, ciphertext).decode())

if __name__ == "__main__":
    main()

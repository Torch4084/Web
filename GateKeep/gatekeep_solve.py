import hashlib
TARGET_MD5 = "47797f54b0f9f4b5b46463e7f86655d5"
MASK = 0xff
def add(a, b):
    return (a + b) & MASK
def sub(a, b):
    return (a - b) & MASK
def inv(a):
    return (~a) & MASK

hits = []
for c5 in range(256):
    for c9 in range(256):
        if add(c9, c5) != 0xa5:
            continue
        if (c9 ^ c5) != 0x41:
            continue
        for c1 in range(256):
            if sub(add(c1, c5), c9) != 0x87:
                continue
            for c4 in range(256):
                c1_plus_c4 = add(c1, c4)
                if ((sub(c1, c4) ^ c1_plus_c4) & MASK) != 0x60:
                    continue
                need = 0xbb ^ add(c1, c5)
                if need & c4:
                    continue
                possible_c7 = [
                    c7 for c7 in range(256)
                    if (c7 & inv(c4)) == need
                ]
                possible_c6 = []
                for c6 in range(256):
                    expr = (
                        (c6 & c5)
                        ^ (c9 | c5)
                        ^ (inv(c5) & inv(c6))
                    ) & MASK
                    if expr == 0xb2:
                        possible_c6.append(c6)
                if not possible_c6:
                    continue
                for c2 in range(256):
                    c1_and_c2 = c1 & c2
                    for c8 in range(256):
                        expr_fd = (
                            ((c4 & c5) & c9)
                            | (((c1 & c8) & c2) ^ add(c2, c8))
                        ) & MASK
                        if expr_fd != 0xfd:
                            continue
                        for c6 in possible_c6:
                            expr_af = add(
                                sub(c9 ^ c6, c8 & c6),
                                sub(c9, inv(c1_and_c2)),
                            )
                            if expr_af != 0xaf:
                                continue
                            for c3 in range(256):
                                expr_45 = (
                                    add(add(c3, c1), c2)
                                    | (c1_and_c2 & c1_plus_c4)
                                ) & MASK
                                if expr_45 != 0x45:
                                    continue
                                for c7 in possible_c7:
                                    password = bytes([
                                        c1, c2, c3,
                                        c4, c5, c6,
                                        c7, c8, c9,
                                    ])
                                    if hashlib.md5(password).hexdigest() == TARGET_MD5:
                                        hits.append(password)
print("hits:", hits)
if hits:
    pwd = hits[0]
    import hashlib
    md5 = hashlib.md5(pwd).hexdigest()
    sha = hashlib.sha256(pwd).hexdigest()
    print(f"password: {pwd!r}")
    print(f"md5:      {md5}")
    print(f"sha256:   {sha}")
    print(f"flag:     omniCTF{{{sha}}}")
    print(f"MD5 matches target: {md5 == TARGET_MD5}")

"""Run the password hashing functions standalone.

Usage: venv/Scripts/python scripts/test_auth.py
"""
import hashlib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from modules.auth import generate_token, hash_password, verify_password

failures = 0


def check(label: str, condition: bool) -> None:
    global failures
    print(f"{label:55s} {'ok' if condition else 'FAILED'}")
    if not condition:
        failures += 1


h1 = hash_password("correct horse battery staple")
h2 = hash_password("correct horse battery staple")

check("hash has 4 $-separated parts", len(h1.split("$")) == 4)
check("hashing the same password twice gives different hashes (random salt)", h1 != h2)
check("verify_password accepts the correct password", verify_password("correct horse battery staple", h1))
check("verify_password rejects a wrong password", not verify_password("wrong password", h1))
check("verify_password rejects an empty password against a real hash", not verify_password("", h1))
check("verify_password handles a malformed hash without raising", not verify_password("x", "not-a-real-hash"))
check("verify_password handles an empty hash without raising", not verify_password("x", ""))

# A hash made under a lower iteration count (as if _ITERATIONS was raised after it was created)
# must still verify -- the count travels with the hash, not with the current module constant.
old_hash = "pbkdf2_sha256$1000$aabbccdd$" + hashlib.pbkdf2_hmac(
    "sha256", b"legacy password", bytes.fromhex("aabbccdd"), 1000
).hex()
check("a hash made under a lower iteration count still verifies", verify_password("legacy password", old_hash))

t1, t2 = generate_token(), generate_token()
check("generate_token returns a non-empty string", isinstance(t1, str) and len(t1) > 20)
check("generate_token returns a different value each time", t1 != t2)

if failures:
    sys.exit(f"\n{failures} check(s) failed.")
print("\nAll checks passed.")

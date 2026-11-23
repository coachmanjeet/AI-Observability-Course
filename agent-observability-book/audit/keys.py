"""The receipt writer's signing key (Chapter 7).

A lab key from a fixed seed, so every output in the book repeats. In
production the private key lives in a KMS or HSM that only the
receipt writer can call, and verifiers hold only the public key.
"""
import base64
import hashlib

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey)

KEY_ID = "pronto-receipts-2026-11"


def lab_key(key_id=KEY_ID):
    seed = hashlib.sha256(key_id.encode()).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))

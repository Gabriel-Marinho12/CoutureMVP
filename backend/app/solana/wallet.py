"""The platform fee-payer keypair, stored in Solana CLI format (JSON array of 64 bytes)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from solders.keypair import Keypair


def load_keypair(path: Path) -> Keypair:
    raw = os.environ.get("COUTURE_KEYPAIR")  # lets container deployments inject the key
    if raw is None:
        if not path.exists():
            raise FileNotFoundError(
                f"platform keypair not found at {path}; create one with `python -m app.cli wallet --create`"
            )
        raw = path.read_text()
    secret = json.loads(raw)
    if not (isinstance(secret, list) and len(secret) == 64):
        raise ValueError("keypair must be a JSON array of 64 bytes (Solana CLI format)")
    return Keypair.from_bytes(bytes(secret))


def create_keypair(path: Path) -> Keypair:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing keypair at {path}")
    keypair = Keypair()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(list(bytes(keypair)), fh)
    return keypair

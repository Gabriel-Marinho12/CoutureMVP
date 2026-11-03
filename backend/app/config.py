"""Runtime settings, read once from the environment (and an optional .env file)."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

DEFAULT_RPC = {
    "devnet": "https://api.devnet.solana.com",
    "testnet": "https://api.testnet.solana.com",
    "mainnet-beta": "https://api.mainnet-beta.solana.com",
    "localnet": "http://127.0.0.1:8899",  # solana-test-validator
}

# A principal is the designer/studio an access key acts for. Every design and
# certificate records the principal that created it, and ownership checks
# compare against it (see SECURITY RULES in CLAUDE.md).
PRINCIPAL = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
DEFAULT_PRINCIPAL = "default"
DEV_PRINCIPAL = "dev"  # used for every request when auth is disabled (development only)


@dataclass(frozen=True)
class Settings:
    cluster: str
    rpc_urls: tuple[str, ...]
    commitment: str
    keypair_path: Path
    data_dir: Path
    api_keys: Mapping[str, str]  # access key -> principal
    cors_origins: tuple[str, ...]
    public_base_url: str
    max_upload_bytes: int
    priority_fee_microlamports: int
    node_bin: str
    merkle_tree: str | None
    frontend_dir: Path | None
    cert_limit_per_hour: int = 30
    max_certs_per_design: int = 500

    @property
    def expose_docs(self) -> bool:
        return self.cluster != "mainnet-beta"

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_keys)

    def explorer_tx(self, signature: str) -> str:
        return self._explorer(f"tx/{signature}")

    def explorer_address(self, address: str) -> str:
        return self._explorer(f"address/{address}")

    def _explorer(self, path: str) -> str:
        if self.cluster == "mainnet-beta":
            suffix = ""
        elif self.cluster == "localnet":
            suffix = f"?cluster=custom&customUrl={quote(self.rpc_urls[0], safe='')}"
        else:
            suffix = f"?cluster={self.cluster}"
        return f"https://explorer.solana.com/{path}{suffix}"


def _csv(value: str | None) -> tuple[str, ...]:
    return tuple(item.strip() for item in (value or "").split(",") if item.strip())


def parse_api_keys(value: str | None) -> dict[str, str]:
    """`principal=key,principal2=key2`. A bare `key` acts for the `default` principal."""
    keys: dict[str, str] = {}
    for entry in _csv(value):
        principal, sep, key = entry.partition("=")
        if not sep:
            principal, key = DEFAULT_PRINCIPAL, entry
        principal, key = principal.strip(), key.strip()
        if not PRINCIPAL.match(principal):
            raise ValueError(f"COUTURE_API_KEYS: invalid principal {principal!r} (use lowercase a-z, 0-9, _ or -)")
        if len(key) < 16 or not key.isascii() or not key.isprintable():
            raise ValueError(f"COUTURE_API_KEYS: the key for {principal!r} must be 16+ printable ASCII characters")
        if key in keys:
            raise ValueError("COUTURE_API_KEYS: the same key is assigned to two principals")
        keys[key] = principal
    return keys

def load_settings() -> Settings:
    load_dotenv(BACKEND_DIR / ".env")
    env = os.environ.get

    cluster = env("SOLANA_CLUSTER", "devnet")
    if cluster not in DEFAULT_RPC:
        raise ValueError(f"SOLANA_CLUSTER must be one of {sorted(DEFAULT_RPC)}, got {cluster!r}")

    data_dir = Path(env("COUTURE_DATA_DIR", str(BACKEND_DIR / "data"))).resolve()
    frontend_dir = REPO_DIR / "frontend"

    settings = Settings(
        cluster=cluster,
        rpc_urls=_csv(env("SOLANA_RPC_URLS")) or (DEFAULT_RPC[cluster],),
        commitment=env("SOLANA_COMMITMENT", "confirmed"),
        keypair_path=Path(env("COUTURE_KEYPAIR_PATH", str(BACKEND_DIR / ".secrets" / "platform-keypair.json"))),
        data_dir=data_dir,
        api_keys=parse_api_keys(env("COUTURE_API_KEYS")),
        cors_origins=_csv(env("COUTURE_CORS_ORIGINS")) or ("https://gabriel-marinho12.github.io",),
        public_base_url=env("COUTURE_PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/"),
        max_upload_bytes=int(env("COUTURE_MAX_UPLOAD_MB", "50")) * 1024 * 1024,
        priority_fee_microlamports=int(env("SOLANA_PRIORITY_FEE_MICROLAMPORTS", "0")),
        node_bin=env("COUTURE_NODE_BIN", "node"),
        merkle_tree=env("COUTURE_MERKLE_TREE") or None,
        frontend_dir=frontend_dir if frontend_dir.is_dir() else None,
        cert_limit_per_hour=int(env("COUTURE_CERT_LIMIT_PER_HOUR", "30")),
        max_certs_per_design=int(env("COUTURE_MAX_CERTS_PER_DESIGN", "500")),
    )

    if settings.cluster == "mainnet-beta" and not settings.auth_enabled:
        raise ValueError("COUTURE_API_KEYS is required on mainnet-beta: refusing to expose paid endpoints unauthenticated")
    return settings

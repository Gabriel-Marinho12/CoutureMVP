"""Runtime settings, read once from the environment (and an optional .env file)."""

from __future__ import annotations

import os
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


@dataclass(frozen=True)
class Settings:
    cluster: str
    rpc_urls: tuple[str, ...]
    commitment: str
    keypair_path: Path
    data_dir: Path
    api_keys: frozenset[str]
    cors_origins: tuple[str, ...]
    public_base_url: str
    max_upload_bytes: int
    priority_fee_microlamports: int
    node_bin: str
    merkle_tree: str | None
    frontend_dir: Path | None

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
        api_keys=frozenset(_csv(env("COUTURE_API_KEYS"))),
        cors_origins=_csv(env("COUTURE_CORS_ORIGINS")) or ("https://gabriel-marinho12.github.io",),
        public_base_url=env("COUTURE_PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/"),
        max_upload_bytes=int(env("COUTURE_MAX_UPLOAD_MB", "50")) * 1024 * 1024,
        priority_fee_microlamports=int(env("SOLANA_PRIORITY_FEE_MICROLAMPORTS", "0")),
        node_bin=env("COUTURE_NODE_BIN", "node"),
        merkle_tree=env("COUTURE_MERKLE_TREE") or None,
        frontend_dir=frontend_dir if frontend_dir.is_dir() else None,
    )

    if settings.cluster == "mainnet-beta" and not settings.auth_enabled:
        raise ValueError("COUTURE_API_KEYS is required on mainnet-beta: refusing to expose paid endpoints unauthenticated")
    return settings

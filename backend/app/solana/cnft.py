"""Compressed NFT certificates via Metaplex Bubblegum V2.

Metaplex ships official SDKs for JavaScript and Rust only, so the on-chain
work runs in a small Node sidecar (backend/metaplex/cnft.mjs) built on the
official `@metaplex-foundation/mpl-bubblegum` package. This module drives it
and adds a second layer of retries for failures the sidecar reports as safe
to retry (nothing landed on-chain).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from solders.pubkey import Pubkey

from ..config import BACKEND_DIR, Settings
from .rpc import ConfirmationUnknown, SolanaError, TransactionFailed

log = logging.getLogger(__name__)

SIDECAR = BACKEND_DIR / "metaplex" / "cnft.mjs"


class CnftUnavailable(SolanaError):
    """The sidecar cannot run (Node or its dependencies are missing)."""


@dataclass(frozen=True)
class MintResult:
    signature: str
    slot: int
    asset_id: str | None


@dataclass(frozen=True)
class TreeResult:
    tree: str
    signature: str
    capacity: int


class CnftMinter:
    def __init__(self, settings: Settings, *, attempts: int = 3, timeout: float = 180.0, script: Path = SIDECAR):
        self.settings = settings
        self.attempts = attempts
        self.timeout = timeout
        self.script = script

    def check_installed(self) -> str | None:
        """None when ready, otherwise a human-readable reason."""
        if not (self.script.parent / "node_modules" / "@metaplex-foundation" / "mpl-bubblegum").is_dir():
            return f"run `npm install` in {self.script.parent}"
        return None

    async def create_tree(self, *, max_depth: int = 14, max_buffer_size: int = 64, canopy_depth: int = 0) -> TreeResult:
        result = await self._run_with_retries(
            "create-tree", {"maxDepth": max_depth, "maxBufferSize": max_buffer_size, "canopyDepth": canopy_depth}
        )
        return TreeResult(result["tree"], result["signature"], int(result["capacity"]))

    async def mint(self, *, tree: str, owner: str, name: str, uri: str) -> MintResult:
        Pubkey.from_string(owner)  # fail fast on a malformed wallet address
        result = await self._run_with_retries("mint", {"tree": tree, "owner": owner, "name": name, "uri": uri})
        return MintResult(result["signature"], int(result["slot"]), result.get("assetId"))

    async def _run_with_retries(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(self.attempts):
            response = await self._run(command, payload)
            if response.get("ok"):
                return response
            error = response.get("error") or {}
            kind, message = error.get("kind"), error.get("message", "unknown sidecar error")
            if kind == "unknown":
                raise ConfirmationUnknown(error.get("signature") or "", message)
            if kind != "retryable" or attempt + 1 == self.attempts:
                raise TransactionFailed(message, error.get("signature"))
            delay = min(8.0, 1.0 * 2**attempt) * random.uniform(0.5, 1.0)
            log.warning("cnft %s failed (%s), retrying in %.1fs", command, message, delay)
            await asyncio.sleep(delay)
        raise AssertionError("unreachable")

    async def _run(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        reason = self.check_installed()
        if reason:
            raise CnftUnavailable(reason)
        env = {
            **os.environ,
            "SOLANA_RPC_URLS": ",".join(self.settings.rpc_urls),
            "SOLANA_COMMITMENT": self.settings.commitment,
            "COUTURE_KEYPAIR_PATH": str(self.settings.keypair_path),
        }
        try:
            proc = await asyncio.create_subprocess_exec(
                self.settings.node_bin, str(self.script), command,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                cwd=self.script.parent, env=env,
            )
        except FileNotFoundError as exc:
            raise CnftUnavailable(f"Node.js not found ({self.settings.node_bin})") from exc

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(json.dumps(payload).encode()), self.timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            # A transaction may already be in flight; its signature is unknown here.
            raise ConfirmationUnknown("", f"cnft {command} timed out after {self.timeout:.0f}s")

        if stderr:
            log.debug("cnft %s stderr:\n%s", command, stderr.decode(errors="replace"))
        lines = stdout.decode(errors="replace").strip().splitlines()
        try:
            return json.loads(lines[-1])
        except (IndexError, json.JSONDecodeError) as exc:
            # The sidecar reports every handled error as JSON, so this is a hard
            # crash at an unknown point: it may have broadcast already.
            tail = stderr.decode(errors="replace")[-500:]
            raise ConfirmationUnknown("", f"cnft sidecar crashed (exit {proc.returncode}): {tail}") from exc

"""Registration and certification workflows.

On-chain work runs in background tasks decoupled from the HTTP request: a
designer closing the tab does not abort a registration, and progress events
are kept so any listener (or a late one) can follow along.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from solders.keypair import Keypair

from . import imaging
from .config import Settings
from .solana import memo
from .solana.cnft import CnftMinter, CnftUnavailable
from .solana.rpc import ConfirmationUnknown, InsufficientFunds, SolanaError, SolanaRpc, TransactionFailed
from .storage import CONFIRMED, FAILED, PENDING, UNCONFIRMED, Certificate, Design, Store

log = logging.getLogger(__name__)

TERMINAL_EVENTS = {"confirmed", "failed", "unconfirmed"}
JOB_RETENTION_SECONDS = 600
SETTLE_AFTER_SECONDS = 300


@dataclass
class Job:
    events: list[dict[str, Any]] = field(default_factory=list)
    changed: asyncio.Condition = field(default_factory=asyncio.Condition)
    finished_at: float | None = None

    async def emit(self, event: str, **data: Any) -> None:
        async with self.changed:
            self.events.append({"event": event, **data})
            if event in TERMINAL_EVENTS:
                self.finished_at = time.monotonic()
            self.changed.notify_all()

    async def follow(self) -> AsyncIterator[dict[str, Any]]:
        index = 0
        while True:
            async with self.changed:
                await self.changed.wait_for(lambda: len(self.events) > index)
                batch = self.events[index:]
            index += len(batch)
            for event in batch:
                yield event
                if event["event"] in TERMINAL_EVENTS:
                    return


class Registrar:
    def __init__(self, settings: Settings, store: Store, rpc: SolanaRpc, payer: Keypair, minter: CnftMinter):
        self.settings = settings
        self.store = store
        self.rpc = rpc
        self.payer = payer
        self.minter = minter
        self._jobs: dict[str, Job] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    # ---- public view of records -----------------------------------------

    def design_view(self, design: Design) -> dict[str, Any]:
        data = design.to_dict()
        data["explorer_url"] = self.settings.explorer_tx(design.signature) if design.signature else None
        data["memo"] = memo.build_memo(design.sha256, design.id)
        return data

    def certificate_view(self, cert: Certificate) -> dict[str, Any]:
        data = cert.to_dict()
        data["explorer_url"] = self.settings.explorer_tx(cert.signature) if cert.signature else None
        data["asset_explorer_url"] = self.settings.explorer_address(cert.asset_id) if cert.asset_id else None
        data["metadata_uri"] = self.metadata_uri(cert.id)
        return data

    def metadata_uri(self, cert_id: str) -> str:
        return f"{self.settings.public_base_url}/api/certificates/{cert_id}/metadata.json"

    # ---- registration -------------------------------------------------------

    def job(self, design_id: str) -> Job | None:
        return self._jobs.get(design_id)

    async def start_registration(self, design: Design) -> Job:
        """`design` must be a pending record the caller has just claimed."""
        self._prune_jobs()
        job = self._jobs[design.id] = Job()
        task = asyncio.create_task(self._register(design, job), name=f"register-{design.id}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job

    async def make_preview(self, design: Design) -> Design:
        mark = f"COUTURE  ·  {design.sha256[:12]}"
        ok = await asyncio.to_thread(
            imaging.make_preview, self.store.original_path(design.sha256), self.store.preview_path(design.id), mark
        )
        return self.store.update_design(design.id, has_preview=int(ok)) if ok != design.has_preview else design

    async def _register(self, design: Design, job: Job) -> None:
        async def broadcast(signature: str) -> None:
            self.store.update_design(design.id, signature=signature)
            await job.emit("submitted", signature=signature, explorer_url=self.settings.explorer_tx(signature))

        await job.emit("submitting", memo=memo.build_memo(design.sha256, design.id))
        try:
            confirmation = await memo.register_hash(
                self.rpc, self.payer, design.sha256, design.id,
                priority_fee_microlamports=self.settings.priority_fee_microlamports,
                on_broadcast=broadcast,
            )
        except ConfirmationUnknown as exc:
            updated = self.store.update_design(design.id, status=UNCONFIRMED, signature=exc.signature, error=str(exc))
            await job.emit("unconfirmed", message="Submitted, awaiting network confirmation.",
                           design=self.design_view(updated))
        except InsufficientFunds:
            updated = self.store.update_design(design.id, status=FAILED, error="platform wallet out of SOL")
            log.error("platform wallet %s needs funding", self.payer.pubkey())
            await job.emit("failed", message="Registration is temporarily unavailable. Please try again later.",
                           retryable=True, design=self.design_view(updated))
        except (SolanaError, Exception) as exc:  # noqa: BLE001 - record every failure
            log.exception("registration of %s failed", design.id)
            retryable = not isinstance(exc, TransactionFailed)
            updated = self.store.update_design(design.id, status=FAILED, error=str(exc)[:500])
            await job.emit("failed", message="The network rejected the registration." if not retryable
                           else "The network is unreachable right now. Please try again.",
                           retryable=retryable, design=self.design_view(updated))
        else:
            updated = self.store.update_design(
                design.id, status=CONFIRMED, signature=confirmation.signature, slot=confirmation.slot, error=None
            )
            await job.emit("confirmed", design=self.design_view(updated))

    def _prune_jobs(self) -> None:
        cutoff = time.monotonic() - JOB_RETENTION_SECONDS
        for key in [k for k, job in self._jobs.items() if job.finished_at and job.finished_at < cutoff]:
            del self._jobs[key]

    # ---- certificates -------------------------------------------------------

    def merkle_tree(self) -> str | None:
        return self.settings.merkle_tree or self.store.get_value("merkle_tree")

    async def issue_certificate(self, design: Design, owner: str) -> Certificate:
        tree = self.merkle_tree()
        if not tree:
            raise CnftUnavailable("no Merkle tree configured; run `python -m app.cli create-tree`")
        cert = self.store.create_certificate(design.id, owner)
        name = f"Couture · {design.title}"
        try:
            result = await self.minter.mint(tree=tree, owner=owner, name=name, uri=self.metadata_uri(cert.id))
        except ConfirmationUnknown as exc:
            return self.store.update_certificate(cert.id, status=UNCONFIRMED, signature=exc.signature or None,
                                                 error=str(exc)[:500])
        except CnftUnavailable as exc:
            self.store.update_certificate(cert.id, status=FAILED, error=str(exc))
            raise
        except Exception as exc:  # noqa: BLE001 - record every failure
            log.exception("certificate %s failed", cert.id)
            return self.store.update_certificate(cert.id, status=FAILED, error=str(exc)[:500])
        return self.store.update_certificate(
            cert.id, status=CONFIRMED, signature=result.signature, asset_id=result.asset_id, error=None
        )

    # ---- recovery ---------------------------------------------------------

    async def recover(self) -> None:
        """Settle records left in flight by a crash or an unknown outcome."""
        for design in self.store.designs_in(PENDING, UNCONFIRMED):
            if design.id in self._jobs:
                continue
            await self._settle_design(design)
        for cert in self.store.certificates_in(PENDING, UNCONFIRMED):
            await self._settle_certificate(cert)

    async def _settle_design(self, design: Design) -> None:
        if not design.signature:
            self.store.update_design(design.id, status=FAILED, error="interrupted before broadcast")
            return
        try:
            status = await self.rpc.signature_status(design.signature)
        except SolanaError as exc:
            log.warning("cannot reconcile %s yet: %s", design.id, exc)
            return
        if status and status.get("err") is None and status.get("confirmationStatus") in ("confirmed", "finalized"):
            self.store.update_design(design.id, status=CONFIRMED, slot=status["slot"], error=None)
        elif status and status.get("err") is not None:
            self.store.update_design(design.id, status=FAILED, error=f"transaction failed: {status['err']}")
        elif _age_seconds(design.created_at) > SETTLE_AFTER_SECONDS:
            # Blockhashes expire after ~90 s: an absent signature this old can never land.
            self.store.update_design(design.id, status=FAILED, error="transaction never landed")
        else:
            self.store.update_design(design.id, status=UNCONFIRMED)

    async def _settle_certificate(self, cert: Certificate) -> None:
        if not cert.signature:
            # The sidecar does not report its signature before finishing, so
            # an interrupted mint cannot be checked automatically.
            self.store.update_certificate(cert.id, status=UNCONFIRMED,
                                          error="interrupted; verify the owner's wallet before re-issuing")
            return
        try:
            status = await self.rpc.signature_status(cert.signature)
        except SolanaError:
            return
        if status and status.get("err") is None and status.get("confirmationStatus") in ("confirmed", "finalized"):
            self.store.update_certificate(cert.id, status=CONFIRMED, error=None)
        elif status and status.get("err") is not None:
            self.store.update_certificate(cert.id, status=FAILED, error=f"transaction failed: {status['err']}")


def _age_seconds(timestamp: str) -> float:
    return (datetime.now(timezone.utc) - datetime.fromisoformat(timestamp)).total_seconds()

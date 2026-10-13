"""Resilient Solana JSON-RPC client.

Every call fails over across the configured endpoints and retries transient
failures (timeouts, connection errors, HTTP 429/5xx, unhealthy-node codes) with
exponential backoff and jitter.

`send_and_confirm` never risks a double submission: a signed transaction is
rebroadcast unchanged until it is confirmed or its blockhash has provably
expired, and only then is it rebuilt with a fresh blockhash. If the outcome
cannot be determined, `ConfirmationUnknown` carries the signature so callers
can reconcile later instead of resubmitting.
"""

from __future__ import annotations

import asyncio
import base64
import inspect
import itertools
import logging
import random
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

import httpx
from solders.hash import Hash
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

log = logging.getLogger(__name__)

# JSON-RPC error codes that describe the node, not the request.
# -32004 block not available, -32005 node unhealthy, -32007 slot skipped,
# -32014 block status not yet available, -32016 min context slot not reached,
# -32603 internal error.
TRANSIENT_RPC_CODES = frozenset({-32004, -32005, -32007, -32014, -32016, -32603})
PREFLIGHT_FAILURE = -32002

COMMITMENT_RANK = {"processed": 0, "confirmed": 1, "finalized": 2}


class SolanaError(Exception):
    """Base class for every error raised by this module."""


class TransientRpcError(SolanaError):
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class RpcUnavailable(SolanaError):
    """Every endpoint failed on every attempt."""


class RpcResponseError(SolanaError):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(f"RPC error {code}: {message}")
        self.code = code
        self.data = data


class BlockhashNotFound(SolanaError):
    """The node no longer (or not yet) knows the transaction's blockhash."""


class TransactionFailed(SolanaError):
    """The transaction was rejected or executed with an error. Nothing to retry."""

    def __init__(self, message: str, signature: str | None = None, err: Any = None, logs: Sequence[str] = ()):
        super().__init__(message)
        self.signature = signature
        self.err = err
        self.logs = list(logs)


class InsufficientFunds(TransactionFailed):
    """The fee payer cannot cover the transaction."""


class TransactionExpired(SolanaError):
    """Every attempt expired without landing. Safe to retry from scratch."""


class ConfirmationUnknown(SolanaError):
    """Broadcast but not confirmed in time. It may still land: reconcile, never resubmit."""

    def __init__(self, signature: str, message: str = "transaction outcome unknown"):
        super().__init__(f"{message} ({signature})")
        self.signature = signature


@dataclass(frozen=True)
class RetryPolicy:
    rounds: int = 4
    base_delay: float = 0.25
    max_delay: float = 4.0

    def delay(self, attempt: int, retry_after: float | None = None) -> float:
        backoff = min(self.max_delay, self.base_delay * 2**attempt) * random.uniform(0.5, 1.0)
        return min(self.max_delay, max(backoff, retry_after or 0.0))


@dataclass(frozen=True)
class Confirmation:
    signature: str
    slot: int


OnBroadcast = Callable[[str], Awaitable[None] | None]


class SolanaRpc:
    def __init__(
        self,
        urls: Sequence[str],
        *,
        commitment: str = "confirmed",
        timeout: float = 10.0,
        policy: RetryPolicy = RetryPolicy(),
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not urls:
            raise ValueError("at least one RPC URL is required")
        if commitment not in COMMITMENT_RANK:
            raise ValueError(f"unknown commitment {commitment!r}")
        self.urls = list(urls)
        self.commitment = commitment
        self.policy = policy
        self._active = 0
        self._ids = itertools.count(1)
        self._http = httpx.AsyncClient(timeout=timeout, transport=transport)

    async def aclose(self) -> None:
        await self._http.aclose()

    # ---- transport -------------------------------------------------------

    async def call(self, method: str, params: list[Any] | None = None) -> Any:
        last: TransientRpcError | None = None
        for attempt in range(self.policy.rounds):
            for offset in range(len(self.urls)):
                index = (self._active + offset) % len(self.urls)
                try:
                    result = await self._post(self.urls[index], method, params or [])
                except TransientRpcError as exc:
                    log.warning("rpc %s via %s failed: %s", method, self.urls[index], exc)
                    last = exc
                    continue
                self._active = index
                return result
            if attempt + 1 < self.policy.rounds:
                await asyncio.sleep(self.policy.delay(attempt, last.retry_after if last else None))
        raise RpcUnavailable(f"{method} failed on all {len(self.urls)} endpoint(s): {last}") from last

    async def _post(self, url: str, method: str, params: list[Any]) -> Any:
        payload = {"jsonrpc": "2.0", "id": next(self._ids), "method": method, "params": params}
        try:
            response = await self._http.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise TransientRpcError(f"{type(exc).__name__}: {exc}") from exc

        if response.status_code == 429 or response.status_code >= 500:
            raise TransientRpcError(f"HTTP {response.status_code}", _retry_after(response))
        if response.status_code != 200:
            # 401/403/404 mean this endpoint rejects us; another one may not.
            raise TransientRpcError(f"HTTP {response.status_code}")
        try:
            body = response.json()
        except ValueError as exc:
            raise TransientRpcError("malformed JSON response") from exc

        error = body.get("error")
        if error:
            code, message = error.get("code", 0), error.get("message", "")
            if code in TRANSIENT_RPC_CODES:
                raise TransientRpcError(f"RPC error {code}: {message}")
            raise RpcResponseError(code, message, error.get("data"))
        return body.get("result")

    # ---- typed helpers ---------------------------------------------------

    async def latest_blockhash(self) -> tuple[Hash, int]:
        result = await self.call("getLatestBlockhash", [{"commitment": self.commitment}])
        value = result["value"]
        return Hash.from_string(value["blockhash"]), int(value["lastValidBlockHeight"])

    async def block_height(self) -> int:
        return int(await self.call("getBlockHeight", [{"commitment": self.commitment}]))

    async def balance(self, pubkey: Pubkey) -> int:
        result = await self.call("getBalance", [str(pubkey), {"commitment": self.commitment}])
        return int(result["value"])

    async def request_airdrop(self, pubkey: Pubkey, lamports: int) -> str:
        return await self.call("requestAirdrop", [str(pubkey), lamports, {"commitment": self.commitment}])

    async def signature_status(self, signature: str) -> dict[str, Any] | None:
        result = await self.call("getSignatureStatuses", [[signature], {"searchTransactionHistory": True}])
        return result["value"][0]

    async def send_transaction(self, tx: VersionedTransaction, *, skip_preflight: bool = False) -> str:
        encoded = base64.b64encode(bytes(tx)).decode()
        options = {
            "encoding": "base64",
            "skipPreflight": skip_preflight,
            "preflightCommitment": self.commitment,
            "maxRetries": 0,  # we rebroadcast ourselves
        }
        try:
            return await self.call("sendTransaction", [encoded, options])
        except RpcResponseError as exc:
            raise _classify_send_error(exc, str(tx.signatures[0])) from exc

    # ---- submission ------------------------------------------------------

    async def send_and_confirm(
        self,
        build: Callable[[Hash], VersionedTransaction],
        *,
        on_broadcast: OnBroadcast | None = None,
        confirm_timeout: float = 90.0,
        rebroadcast_interval: float = 2.0,
        max_rebuilds: int = 3,
    ) -> Confirmation:
        """Sign via `build(blockhash)`, submit, and wait for `self.commitment`."""
        for _ in range(max_rebuilds + 1):
            blockhash, last_valid_height = await self.latest_blockhash()
            tx = build(blockhash)
            signature = str(tx.signatures[0])

            try:
                await self.send_transaction(tx)
            except BlockhashNotFound:
                log.info("blockhash rejected before broadcast, rebuilding")
                continue
            except RpcUnavailable:
                # The node may have received it anyway; polling will tell.
                log.warning("initial broadcast of %s unacknowledged, polling", signature)

            await _maybe_await(on_broadcast, signature)
            try:
                confirmation = await self._await_confirmation(
                    tx, signature, last_valid_height, confirm_timeout, rebroadcast_interval
                )
            except RpcUnavailable as exc:
                raise ConfirmationUnknown(signature, "lost contact with the network") from exc
            if confirmation:
                return confirmation
            log.info("transaction %s expired without landing, rebuilding", signature)

        raise TransactionExpired(f"transaction expired {max_rebuilds + 1} times without landing")

    async def _await_confirmation(
        self,
        tx: VersionedTransaction,
        signature: str,
        last_valid_height: int,
        timeout: float,
        interval: float,
    ) -> Confirmation | None:
        """Confirmation once landed, None once provably expired."""
        deadline = time.monotonic() + timeout
        while True:
            status = await self.signature_status(signature)
            if status:
                if status.get("err") is not None:
                    raise TransactionFailed(f"transaction failed: {status['err']}", signature, status["err"])
                if self._meets_commitment(status.get("confirmationStatus")):
                    return Confirmation(signature, int(status["slot"]))
            elif await self.block_height() > last_valid_height:
                # The blockhash is dead, so the transaction can never land
                # unless it already has; check once more to close the race.
                if await self.signature_status(signature) is None:
                    return None
                continue

            if time.monotonic() >= deadline:
                raise ConfirmationUnknown(signature)
            await asyncio.sleep(interval)
            try:
                await self.send_transaction(tx, skip_preflight=True)
            except SolanaError as exc:
                log.debug("rebroadcast of %s failed: %s", signature, exc)

    def _meets_commitment(self, reached: str | None) -> bool:
        return reached is not None and COMMITMENT_RANK.get(reached, -1) >= COMMITMENT_RANK[self.commitment]


def _retry_after(response: httpx.Response) -> float | None:
    try:
        return float(response.headers["retry-after"])
    except (KeyError, ValueError):
        return None


def _classify_send_error(exc: RpcResponseError, signature: str) -> SolanaError:
    if exc.code != PREFLIGHT_FAILURE:
        return TransactionFailed(str(exc), signature)
    data = exc.data if isinstance(exc.data, dict) else {}
    err = data.get("err")
    logs = data.get("logs") or []
    text = f"{err} {' '.join(logs)} {exc}"
    if "BlockhashNotFound" in text or "Blockhash not found" in text:
        return BlockhashNotFound(str(exc))
    if "InsufficientFunds" in text or "insufficient lamports" in text or err == "AccountNotFound":
        return InsufficientFunds("fee payer has insufficient SOL", signature, err, logs)
    return TransactionFailed(f"transaction simulation failed: {err or exc}", signature, err, logs)


async def _maybe_await(callback: OnBroadcast | None, signature: str) -> None:
    if callback is None:
        return
    result = callback(signature)
    if inspect.isawaitable(result):
        await result

"""Authorship registry: a design's SHA-256 written on-chain with the SPL Memo program (v2)."""

from __future__ import annotations

import re

from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

from .rpc import Confirmation, OnBroadcast, SolanaRpc

MEMO_PROGRAM_ID = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
MEMO_PREFIX = "couture:ip:v1"
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
# Measured: a ~106-byte memo with one signer consumes ~52k compute units.
MEMO_COMPUTE_UNITS = 100_000


def build_memo(sha256_hex: str, reference: str) -> str:
    """Compact, parseable record. No personal data goes on-chain."""
    if not _SHA256_HEX.match(sha256_hex):
        raise ValueError("sha256 must be 64 lowercase hex characters")
    return f"{MEMO_PREFIX} sha256={sha256_hex} ref={reference}"


def memo_instruction(memo: str, signer: Pubkey) -> Instruction:
    return Instruction(
        program_id=MEMO_PROGRAM_ID,
        accounts=[AccountMeta(pubkey=signer, is_signer=True, is_writable=False)],
        data=memo.encode(),
    )


async def register_hash(
    rpc: SolanaRpc,
    payer: Keypair,
    sha256_hex: str,
    reference: str,
    *,
    priority_fee_microlamports: int = 0,
    on_broadcast: OnBroadcast | None = None,
) -> Confirmation:
    instructions = [memo_instruction(build_memo(sha256_hex, reference), payer.pubkey())]
    if priority_fee_microlamports > 0:
        instructions[:0] = [set_compute_unit_limit(MEMO_COMPUTE_UNITS), set_compute_unit_price(priority_fee_microlamports)]

    def build(blockhash: Hash) -> VersionedTransaction:
        message = MessageV0.try_compile(payer.pubkey(), instructions, [], blockhash)
        return VersionedTransaction(message, [payer])

    return await rpc.send_and_confirm(build, on_broadcast=on_broadcast)

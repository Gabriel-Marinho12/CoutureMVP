import json

import httpx
import pytest
from solders.hash import Hash
from solders.keypair import Keypair

from app.solana import memo
from app.solana.rpc import (
    ConfirmationUnknown,
    InsufficientFunds,
    RetryPolicy,
    RpcUnavailable,
    SolanaRpc,
    TransactionFailed,
)

FAST = RetryPolicy(rounds=3, base_delay=0, max_delay=0)


class FakeCluster:
    """Scriptable JSON-RPC endpoint(s) behind an httpx MockTransport."""

    def __init__(self):
        self.calls: list[tuple[str, str]] = []
        self.down: set[str] = set()
        self.height = 100
        self.last_valid = 150
        self.statuses: dict[str, dict | None] = {}
        self.landing_after_sends = 1  # a signature lands after this many sends
        self.sends: dict[str, int] = {}
        self.send_error: dict | None = None

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        body = json.loads(request.content)
        method, params = body["method"], body["params"]
        self.calls.append((host, method))
        if host in self.down:
            return httpx.Response(503)
        result = getattr(self, method)(params)
        if isinstance(result, httpx.Response):
            return result
        if isinstance(result, dict) and "__error__" in result:
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "error": result["__error__"]})
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result})

    def getLatestBlockhash(self, params):
        blockhash = str(Hash.new_unique())  # every rebuild yields a distinct transaction
        return {"context": {"slot": 1}, "value": {"blockhash": blockhash, "lastValidBlockHeight": self.last_valid}}

    def getBlockHeight(self, params):
        return self.height

    def getBalance(self, params):
        return {"context": {"slot": 1}, "value": 5_000}

    def sendTransaction(self, params):
        if self.send_error:
            return {"__error__": self.send_error}
        import base64
        from solders.transaction import VersionedTransaction

        signature = str(VersionedTransaction.from_bytes(base64.b64decode(params[0])).signatures[0])
        self.sends[signature] = self.sends.get(signature, 0) + 1
        if self.sends[signature] >= self.landing_after_sends and signature not in self.statuses:
            self.statuses[signature] = {"slot": 4242, "err": None, "confirmationStatus": "confirmed"}
        return signature

    def getSignatureStatuses(self, params):
        return {"context": {"slot": 1}, "value": [self.statuses.get(params[0][0])]}


def make_rpc(cluster: FakeCluster, urls=("http://a", "http://b")) -> SolanaRpc:
    return SolanaRpc(list(urls), policy=FAST, transport=cluster.transport())


async def register(rpc: SolanaRpc, **kwargs):
    return await memo.register_hash(rpc, Keypair(), "ab" * 32, "ref", **kwargs)


async def test_fails_over_to_healthy_endpoint_and_sticks():
    cluster = FakeCluster()
    cluster.down.add("a")
    rpc = make_rpc(cluster)
    assert await rpc.balance(Keypair().pubkey()) == 5_000
    await rpc.balance(Keypair().pubkey())
    assert [host for host, _ in cluster.calls] == ["a", "b", "b"]


async def test_raises_when_every_endpoint_is_down():
    cluster = FakeCluster()
    cluster.down.update({"a", "b"})
    with pytest.raises(RpcUnavailable):
        await make_rpc(cluster).block_height()
    assert len(cluster.calls) == 6  # 3 rounds x 2 endpoints


async def test_registers_and_reports_broadcast():
    cluster = FakeCluster()
    seen = []
    confirmation = await register(make_rpc(cluster), on_broadcast=seen.append)
    assert confirmation.slot == 4242
    assert seen == [confirmation.signature]


async def test_rebroadcasts_same_signature_until_landed():
    cluster = FakeCluster()
    cluster.landing_after_sends = 3
    rpc = make_rpc(cluster)
    rpc_confirm = rpc.send_and_confirm

    async def quick(build, **kw):
        return await rpc_confirm(build, rebroadcast_interval=0, **kw)

    rpc.send_and_confirm = quick
    confirmation = await register(rpc)
    assert cluster.sends == {confirmation.signature: 3}


async def test_rebuilds_only_after_blockhash_expiry():
    cluster = FakeCluster()
    cluster.landing_after_sends = 10**9  # never lands
    cluster.height = 151  # already past last_valid
    rpc = make_rpc(cluster)
    with pytest.raises(Exception) as info:
        await rpc.send_and_confirm(
            lambda bh: _tx(bh), rebroadcast_interval=0, max_rebuilds=2
        )
    assert type(info.value).__name__ == "TransactionExpired"
    # three distinct transactions, each sent once and never rebroadcast after its blockhash died
    assert sorted(cluster.sends.values()) == [1, 1, 1]


async def test_unknown_outcome_carries_signature():
    cluster = FakeCluster()
    cluster.landing_after_sends = 10**9
    rpc = make_rpc(cluster)
    with pytest.raises(ConfirmationUnknown) as info:
        await rpc.send_and_confirm(lambda bh: _tx(bh), confirm_timeout=0, rebroadcast_interval=0)
    assert info.value.signature in cluster.sends


async def test_insufficient_funds_is_permanent():
    cluster = FakeCluster()
    cluster.send_error = {"code": -32002, "message": "Transaction simulation failed",
                          "data": {"err": "AccountNotFound", "logs": []}}
    with pytest.raises(InsufficientFunds):
        await register(make_rpc(cluster))
    assert sum(1 for _, m in cluster.calls if m == "sendTransaction") == 1


async def test_program_error_is_permanent():
    cluster = FakeCluster()
    cluster.send_error = {"code": -32002, "message": "Transaction simulation failed",
                          "data": {"err": {"InstructionError": [0, "InvalidInstructionData"]}, "logs": []}}
    with pytest.raises(TransactionFailed):
        await register(make_rpc(cluster))


def test_memo_format_rejects_bad_hash():
    assert memo.build_memo("ab" * 32, "x1") == f"couture:ip:v1 sha256={'ab' * 32} ref=x1"
    with pytest.raises(ValueError):
        memo.build_memo("not-a-hash", "x1")


_PAYER = Keypair()


def _tx(blockhash):
    from solders.message import MessageV0
    from solders.transaction import VersionedTransaction

    ix = memo.memo_instruction("hello", _PAYER.pubkey())
    return VersionedTransaction(MessageV0.try_compile(_PAYER.pubkey(), [ix], [], blockhash), [_PAYER])

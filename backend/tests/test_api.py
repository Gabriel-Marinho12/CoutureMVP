import base64
import dataclasses
import hashlib
import io
import json

import httpx
import pytest
from PIL import Image
from solders.keypair import Keypair

from app.config import load_settings
from app.main import create_app
from app.registration import Registrar
from app.solana.cnft import MintResult
from app.solana.rpc import RetryPolicy, SolanaRpc
from app.storage import Store
from tests.test_rpc import FakeCluster

API_KEY = "test-key-atelier-a-0001"
OTHER_KEY = "test-key-atelier-b-0002"
KEYS = {API_KEY: "atelier-a", OTHER_KEY: "atelier-b"}


def auth(key=API_KEY):
    return {"Authorization": f"Bearer {key}"}


class FakeMinter:
    def __init__(self):
        self.minted = []

    def check_installed(self):
        return None

    async def mint(self, **kwargs):
        self.minted.append(kwargs)
        return MintResult("5" * 88, 99, "Asset1111111111111111111111111111111111111")


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("COUTURE_MERKLE_TREE", "Tree111111111111111111111111111111111111111")
    settings = dataclasses.replace(load_settings(), data_dir=tmp_path, api_keys=KEYS, frontend_dir=None,
                                   cert_limit_per_hour=5, max_certs_per_design=500)
    cluster = FakeCluster()
    rpc = SolanaRpc(["http://a"], policy=RetryPolicy(rounds=1, base_delay=0, max_delay=0), transport=cluster.transport())
    store = Store(tmp_path)
    minter = FakeMinter()
    registrar = Registrar(settings, store, rpc, Keypair(), minter)
    app = create_app(settings, registrar=registrar)
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
    client.store = store
    return client, cluster, minter


def png_bytes(color=(120, 20, 40)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), color).save(buffer, "PNG")
    return buffer.getvalue()


async def upload(client, data: bytes, key=API_KEY):
    response = await client.post(
        "/api/designs",
        files={"file": ("gown.png", data, "image/png")},
        data={"title": "Robe Nocturne", "designer": "Atelier Test"},
        headers={"Authorization": f"Bearer {key}"},
    )
    return response, [json.loads(line) for line in response.text.splitlines() if line]


async def test_upload_streams_hash_and_confirmed_transaction(env):
    client, cluster, _ = env
    data = png_bytes()
    response, events = await upload(client, data)
    assert response.status_code == 200
    names = [e["event"] for e in events]
    assert names == ["received", "hashed", "submitting", "submitted", "confirmed"]
    assert events[1]["sha256"] == hashlib.sha256(data).hexdigest()
    design = events[-1]["design"]
    assert design["status"] == "confirmed"
    assert design["explorer_url"].startswith("https://explorer.solana.com/tx/")
    assert design["has_preview"] is True


async def test_duplicate_upload_returns_original_registration(env):
    client, _, _ = env
    data = png_bytes()
    _, first = await upload(client, data)
    _, second = await upload(client, data)
    assert [e["event"] for e in second] == ["received", "hashed", "duplicate"]
    assert second[-1]["design"]["signature"] == first[-1]["design"]["signature"]


async def test_upload_requires_key(env):
    client, _, _ = env
    response, _ = await upload(client, png_bytes(), key="wrong")
    assert response.status_code == 401


async def test_verify_by_hash_and_protected_view(env):
    client, _, _ = env
    data = png_bytes()
    _, events = await upload(client, data)
    design_id = events[-1]["design"]["id"]

    found = await client.get(f"/api/designs/by-hash/{hashlib.sha256(data).hexdigest()}")
    assert found.json()["id"] == design_id
    assert (await client.get(f"/api/designs/by-hash/{'0' * 64}")).status_code == 404

    view = (await client.get(f"/api/designs/{design_id}/view")).json()
    assert sorted(view["order"]) == list(range(view["cols"] * view["rows"]))
    sprite = Image.open(io.BytesIO(base64.b64decode(view["sprite"])))
    pad = view["pad"]
    assert sprite.size == (view["width"] + 2 * pad * view["cols"], view["height"] + 2 * pad * view["rows"])


async def test_failed_network_registration_can_be_retried(env):
    client, cluster, _ = env
    cluster.send_error = {"code": -32002, "message": "simulation failed",
                          "data": {"err": {"InstructionError": [0, "Custom"]}, "logs": []}}
    data = png_bytes((1, 2, 3))
    _, events = await upload(client, data)
    assert events[-1]["event"] == "failed"
    cluster.send_error = None
    _, events = await upload(client, data)
    assert events[-1]["event"] == "confirmed"


async def test_certificate_mint_and_metadata(env):
    client, _, minter = env
    _, events = await upload(client, png_bytes())
    design_id = events[-1]["design"]["id"]
    owner = str(Keypair().pubkey())

    bad = await client.post(f"/api/designs/{design_id}/certificates", json={"owner": "nope", "order_id": "o-1"},
                            headers=auth())
    assert bad.status_code == 422

    response = await client.post(f"/api/designs/{design_id}/certificates", json={"owner": owner, "order_id": "o-1"},
                                 headers=auth())
    assert response.status_code == 201
    cert = response.json()
    assert cert["status"] == "confirmed" and cert["asset_id"]
    assert minter.minted[0]["owner"] == owner
    assert "issued_by" not in cert and "error" not in cert

    metadata = (await client.get(f"/api/certificates/{cert['id']}/metadata.json")).json()
    traits = {a["trait_type"]: a["value"] for a in metadata["attributes"]}
    assert traits["Design SHA-256"] == events[1]["sha256"]
    assert len(metadata["name"]) <= 32


# ---- regression tests for the security audit (see CLAUDE.md) ----------------

async def certify(client, design_id, owner, order_id="o-1", key=API_KEY):
    return await client.post(f"/api/designs/{design_id}/certificates",
                             json={"owner": owner, "order_id": order_id}, headers=auth(key))


async def test_other_principal_cannot_certify_a_design(env):
    client, _, minter = env
    _, events = await upload(client, png_bytes())
    response = await certify(client, events[-1]["design"]["id"], str(Keypair().pubkey()), key=OTHER_KEY)
    assert response.status_code == 403
    assert minter.minted == []


async def test_other_principal_cannot_take_over_a_failed_hash(env):
    client, cluster, _ = env
    cluster.send_error = {"code": -32002, "message": "simulation failed",
                          "data": {"err": {"InstructionError": [0, "Custom"]}, "logs": []}}
    data = png_bytes((9, 9, 9))
    _, events = await upload(client, data)
    assert events[-1]["event"] == "failed"
    cluster.send_error = None
    _, events = await upload(client, data, key=OTHER_KEY)
    assert [e["event"] for e in events] == ["received", "hashed", "duplicate"]


async def test_certificate_is_idempotent_per_order(env):
    client, _, minter = env
    _, events = await upload(client, png_bytes())
    design_id, owner = events[-1]["design"]["id"], str(Keypair().pubkey())
    first = await certify(client, design_id, owner)
    replay = await certify(client, design_id, owner)
    assert (first.status_code, replay.status_code) == (201, 200)
    assert first.json()["id"] == replay.json()["id"]
    assert len(minter.minted) == 1
    other_wallet = await certify(client, design_id, str(Keypair().pubkey()))
    assert other_wallet.status_code == 409


async def test_failed_certificate_can_be_retried_with_same_order(env):
    client, _, minter = env
    _, events = await upload(client, png_bytes())
    design_id, owner = events[-1]["design"]["id"], str(Keypair().pubkey())
    real_mint = minter.mint

    async def failing_mint(**kwargs):
        raise RuntimeError("simulated network rejection")

    minter.mint = failing_mint
    assert (await certify(client, design_id, owner)).status_code == 502
    minter.mint = real_mint
    retry = await certify(client, design_id, owner)
    assert retry.status_code == 201 and retry.json()["status"] == "confirmed"
    assert len(minter.minted) == 1


async def test_certificate_hourly_limit(env):
    client, _, minter = env
    _, events = await upload(client, png_bytes())
    design_id = events[-1]["design"]["id"]
    codes = [(await certify(client, design_id, str(Keypair().pubkey()), order_id=f"o-{i}")).status_code
             for i in range(6)]
    assert codes == [201] * 5 + [429]
    assert len(minter.minted) == 5


async def test_unauthenticated_upload_rejected_before_body_is_read(env):
    client, _, _ = env
    received = []

    async def body():
        for _ in range(4):
            received.append(1)
            yield b"x" * 1024

    response = await client.post("/api/designs", content=body(), headers={"Content-Type": "multipart/form-data"})
    assert response.status_code == 401
    assert received == [] or len(received) <= 1  # the guard answers without consuming the stream


async def test_upload_requires_content_length(env):
    client, _, _ = env

    async def body():
        yield b"--x\r\n"

    response = await client.post("/api/designs", content=body(),
                                 headers={**auth(), "Content-Type": "multipart/form-data; boundary=x"})
    assert response.status_code == 411


async def test_oversized_declared_body_rejected(env):
    client, _, _ = env
    response = await client.post("/api/designs/x/certificates", content=b"{}",
                                 headers={**auth(), "Content-Length": str(10 * 1024 * 1024)})
    assert response.status_code == 413


async def test_non_ascii_authorization_is_401_not_500(env):
    client, _, _ = env
    response = await client.post("/api/designs", content=b"x",
                                 headers={"Authorization": "Bearer café".encode("latin-1")})
    assert response.status_code == 401


async def test_internal_errors_are_not_exposed(env):
    client, cluster, _ = env
    cluster.send_error = {"code": -32002, "message": "simulation failed",
                          "data": {"err": "https://rpc.example/?api-key=SECRET", "logs": []}}
    _, events = await upload(client, png_bytes((4, 5, 6)))
    assert "SECRET" not in json.dumps(events)
    design_id = events[1]["design_id"]
    public = (await client.get(f"/api/designs/{design_id}")).json()
    assert "error" not in public and "owner" not in public
    assert "SECRET" in client.store.get_design(design_id).error  # still kept for operators


async def test_control_characters_are_stripped(env):
    client, _, _ = env
    response = await client.post(
        "/api/designs", files={"file": ("a.png", png_bytes((7, 7, 7)), "image/png")},
        data={"title": "Robe‮ Noir\x00", "designer": "Atelier​ X"}, headers=auth())
    design = [json.loads(line) for line in response.text.splitlines()][-1]["design"]
    assert design["title"] == "Robe Noir" and design["designer"] == "Atelier X"


async def test_corrupt_image_still_registers_without_preview(env):
    client, _, _ = env
    png = png_bytes((3, 3, 3))
    _, events = await upload(client, png[:60])  # truncated PNG: decoder error
    assert events[-1]["event"] == "confirmed"
    assert events[-1]["design"]["has_preview"] is False


async def test_session_validates_key_without_side_effects(env):
    client, _, _ = env
    assert (await client.get("/api/session", headers=auth())).json() == {"principal": "atelier-a"}
    assert (await client.get("/api/session", headers=auth("wrong-key-000000000"))).status_code == 401
    assert (await client.get("/api/health")).json()["max_upload_mb"] > 0


def test_nft_name_fits_32_bytes():
    from app.registration import fit_utf8
    name = fit_utf8("Couture · Robe Nocturne en soie brodée à la main", 32)
    assert len(name.encode()) <= 32 and name.startswith("Couture")


def test_sidecar_env_does_not_leak_api_keys(monkeypatch):
    from app.solana.cnft import sidecar_env
    monkeypatch.setenv("COUTURE_API_KEYS", "a=supersecretkey000000")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "x")
    env = sidecar_env(load_settings())
    assert "COUTURE_API_KEYS" not in env and "AWS_SECRET_ACCESS_KEY" not in env
    assert "SOLANA_RPC_URLS" in env


def test_api_key_parsing():
    from app.config import parse_api_keys
    assert parse_api_keys("atelier-a=aaaaaaaaaaaaaaaa,bbbbbbbbbbbbbbbb") == {
        "aaaaaaaaaaaaaaaa": "atelier-a", "bbbbbbbbbbbbbbbb": "default"}
    with pytest.raises(ValueError):
        parse_api_keys("a=short")
    with pytest.raises(ValueError):
        parse_api_keys("Bad Name=aaaaaaaaaaaaaaaa")

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

API_KEY = "test-key"


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
    settings = dataclasses.replace(load_settings(), data_dir=tmp_path, api_keys=frozenset({API_KEY}), frontend_dir=None)
    cluster = FakeCluster()
    rpc = SolanaRpc(["http://a"], policy=RetryPolicy(rounds=1, base_delay=0, max_delay=0), transport=cluster.transport())
    store = Store(tmp_path)
    minter = FakeMinter()
    registrar = Registrar(settings, store, rpc, Keypair(), minter)
    app = create_app(settings, registrar=registrar)
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
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

    bad = await client.post(f"/api/designs/{design_id}/certificates", json={"owner": "nope"},
                            headers={"Authorization": f"Bearer {API_KEY}"})
    assert bad.status_code == 422

    response = await client.post(f"/api/designs/{design_id}/certificates", json={"owner": owner},
                                 headers={"Authorization": f"Bearer {API_KEY}"})
    assert response.status_code == 201
    cert = response.json()
    assert cert["status"] == "confirmed" and cert["asset_id"]
    assert minter.minted[0]["owner"] == owner

    metadata = (await client.get(f"/api/certificates/{cert['id']}/metadata.json")).json()
    traits = {a["trait_type"]: a["value"] for a in metadata["attributes"]}
    assert traits["Design SHA-256"] == events[1]["sha256"]
    assert len(metadata["name"]) <= 32

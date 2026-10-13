"""HTTP API.

POST /api/designs streams newline-delimited JSON events while a design is
hashed and registered on Solana, so the studio can show each step live:
  received -> hashed -> (duplicate | submitting -> submitted -> confirmed/failed/unconfirmed)
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from solders.pubkey import Pubkey

from . import imaging
from .config import Settings, load_settings
from .registration import Registrar
from .solana.cnft import CnftMinter, CnftUnavailable
from .solana.rpc import SolanaError, SolanaRpc
from .solana.wallet import load_keypair
from .storage import CONFIRMED, Design, Store

log = logging.getLogger("couture")

SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
CHUNK = 1024 * 1024
LOW_BALANCE_LAMPORTS = 10_000_000  # 0.01 SOL ≈ 2,000 registrations


def get_registrar(request: Request) -> Registrar:
    return request.app.state.registrar


Reg = Annotated[Registrar, Depends(get_registrar)]


class CertificateRequest(BaseModel):
    owner: str = Field(description="Buyer's Solana wallet address")


def create_app(settings: Settings | None = None, *, registrar: Registrar | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if registrar is not None:  # injected (tests): the caller owns its lifecycle
            yield
            return
        store = Store(settings.data_dir)
        rpc = SolanaRpc(settings.rpc_urls, commitment=settings.commitment)
        payer = load_keypair(settings.keypair_path)
        app.state.registrar = Registrar(settings, store, rpc, payer, CnftMinter(settings))
        if not settings.auth_enabled:
            log.warning("COUTURE_API_KEYS is empty: write endpoints are open (development mode)")
        log.info("platform wallet %s on %s", payer.pubkey(), settings.cluster)
        reconcile = asyncio.create_task(_reconcile_forever(app.state.registrar))
        try:
            yield
        finally:
            reconcile.cancel()
            await rpc.aclose()
            store.close()

    app = FastAPI(title="Couture", version="1.0.0", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
    if registrar is not None:
        app.state.registrar = registrar
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    def require_key(authorization: Annotated[str | None, Header()] = None) -> None:
        if not settings.auth_enabled:
            return
        token = (authorization or "").removeprefix("Bearer ").strip()
        if not any(hmac.compare_digest(token, key) for key in settings.api_keys):
            raise HTTPException(401, "a valid access key is required", headers={"WWW-Authenticate": "Bearer"})

    # ---- status -------------------------------------------------------------

    @app.get("/api/health")
    async def health(registrar: Reg) -> dict[str, Any]:
        wallet = str(registrar.payer.pubkey())
        try:
            lamports = await registrar.rpc.balance(registrar.payer.pubkey())
            network = "ok"
        except SolanaError:
            lamports, network = None, "unreachable"
        return {
            "status": "ok" if network == "ok" and (lamports or 0) >= LOW_BALANCE_LAMPORTS else "degraded",
            "cluster": settings.cluster,
            "network": network,
            "wallet": wallet,
            "wallet_explorer_url": settings.explorer_address(wallet),
            "balance_sol": lamports / 1e9 if lamports is not None else None,
            "auth_required": settings.auth_enabled,
            "certificates_ready": bool(registrar.merkle_tree()) and registrar.minter.check_installed() is None,
        }

    # ---- designs ------------------------------------------------------------

    @app.post("/api/designs", dependencies=[Depends(require_key)])
    async def register_design(
        registrar: Reg,
        file: Annotated[UploadFile, File()],
        title: Annotated[str, Form(min_length=1, max_length=120)],
        designer: Annotated[str, Form(min_length=1, max_length=120)],
        request: Request,
    ) -> StreamingResponse:
        declared = int(request.headers.get("content-length") or 0)
        if declared > settings.max_upload_bytes + CHUNK:
            raise HTTPException(413, f"files are limited to {settings.max_upload_bytes // (1024 * 1024)} MB")
        sha256, size, tmp_path = await _spool(file, registrar.store.tmp, settings.max_upload_bytes)

        design, owns = registrar.store.claim_design(
            sha256=sha256, title=title.strip(), designer=designer.strip(),
            filename=os.path.basename(file.filename or "design"),
            content_type=file.content_type or "application/octet-stream", size_bytes=size,
        )
        if owns:
            os.replace(tmp_path, registrar.store.original_path(sha256))
            design = await registrar.make_preview(design)
            job = await registrar.start_registration(design)
        else:
            tmp_path.unlink(missing_ok=True)
            job = registrar.job(design.id)

        async def events() -> AsyncIterator[bytes]:
            yield _line({"event": "received", "filename": design.filename, "size_bytes": size})
            yield _line({"event": "hashed", "sha256": sha256, "design_id": design.id})
            if not owns:
                yield _line({"event": "duplicate", "design": registrar.design_view(design)})
                if job is None or design.status == CONFIRMED:
                    return
            async for event in job.follow():
                yield _line(event)

        return StreamingResponse(events(), media_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    @app.get("/api/designs")
    async def list_designs(registrar: Reg, limit: int = 60) -> list[dict[str, Any]]:
        designs = registrar.store.list_designs(status=CONFIRMED, limit=max(1, min(limit, 200)))
        return [registrar.design_view(d) for d in designs]

    @app.get("/api/designs/by-hash/{sha256}")
    async def design_by_hash(sha256: str, registrar: Reg) -> dict[str, Any]:
        sha256 = sha256.lower()
        if not SHA256_HEX.match(sha256):
            raise HTTPException(422, "expected a SHA-256 hex digest")
        design = registrar.store.design_by_hash(sha256)
        if design is None:
            raise HTTPException(404, "no design is registered with this fingerprint")
        return registrar.design_view(design)

    @app.get("/api/designs/{design_id}")
    async def get_design(design_id: str, registrar: Reg) -> dict[str, Any]:
        design = _design_or_404(registrar, design_id)
        view = registrar.design_view(design)
        view["certificates"] = [registrar.certificate_view(c) for c in registrar.store.certificates_for(design.id)]
        return view

    @app.get("/api/designs/{design_id}/view")
    async def protected_view(design_id: str, registrar: Reg, size: int = imaging.PREVIEW_MAX) -> JSONResponse:
        design = _design_or_404(registrar, design_id)
        if not design.has_preview:
            raise HTTPException(404, "this design has no visual preview")
        size = max(160, min(size, imaging.PREVIEW_MAX))
        view = await asyncio.to_thread(imaging.scrambled_view, registrar.store.preview_path(design.id), imaging.GRID, size)
        return JSONResponse(
            {
                "width": view.width, "height": view.height, "cols": view.cols, "rows": view.rows,
                "pad": view.pad, "order": view.order, "sprite": base64.b64encode(view.webp).decode(),
            },
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/designs/{design_id}/thumbnail.webp")
    async def design_thumbnail(design_id: str, registrar: Reg) -> Response:
        design = _design_or_404(registrar, design_id)
        if not design.has_preview:
            raise HTTPException(404, "this design has no visual preview")
        data = await asyncio.to_thread(imaging.thumbnail, registrar.store.preview_path(design.id))
        return Response(data, media_type="image/webp", headers={"Cache-Control": "public, max-age=86400"})

    # ---- certificates -------------------------------------------------------

    @app.post("/api/designs/{design_id}/certificates", dependencies=[Depends(require_key)], status_code=201)
    async def issue_certificate(design_id: str, body: CertificateRequest, registrar: Reg) -> JSONResponse:
        design = _design_or_404(registrar, design_id)
        if design.status != CONFIRMED:
            raise HTTPException(409, "the design must be registered on-chain before certificates are issued")
        try:
            Pubkey.from_string(body.owner.strip())
        except ValueError:
            raise HTTPException(422, "owner is not a valid Solana address") from None
        try:
            cert = await registrar.issue_certificate(design, body.owner.strip())
        except CnftUnavailable as exc:
            raise HTTPException(503, f"certificates are not configured: {exc}") from exc
        status = {"confirmed": 201, "unconfirmed": 202}.get(cert.status, 502)
        return JSONResponse(registrar.certificate_view(cert), status_code=status)

    @app.get("/api/certificates/{cert_id}")
    async def get_certificate(cert_id: str, registrar: Reg) -> dict[str, Any]:
        cert = registrar.store.get_certificate(cert_id)
        if cert is None:
            raise HTTPException(404, "certificate not found")
        view = registrar.certificate_view(cert)
        view["design"] = registrar.design_view(_design_or_404(registrar, cert.design_id))
        return view

    @app.get("/api/certificates/{cert_id}/metadata.json")
    async def certificate_metadata(cert_id: str, registrar: Reg) -> dict[str, Any]:
        """Metaplex token metadata standard, read by wallets and explorers."""
        cert = registrar.store.get_certificate(cert_id)
        if cert is None:
            raise HTTPException(404, "certificate not found")
        design = _design_or_404(registrar, cert.design_id)
        image = f"{settings.public_base_url}/api/designs/{design.id}/thumbnail.webp" if design.has_preview else ""
        return {
            "name": f"Couture · {design.title}"[:32],
            "symbol": "COUTURE",
            "description": (
                f"Certificate of authenticity for “{design.title}” by {design.designer}. "
                f"Design fingerprint SHA-256 {design.sha256}, registered on Solana "
                f"({settings.cluster}) in transaction {design.signature}."
            ),
            "image": image,
            "external_url": f"{settings.public_base_url}/#verify/{design.sha256}",
            "attributes": [
                {"trait_type": "Designer", "value": design.designer},
                {"trait_type": "Design SHA-256", "value": design.sha256},
                {"trait_type": "Registry transaction", "value": design.signature},
                {"trait_type": "Registered at", "value": design.registered_at},
                {"trait_type": "Certificate", "value": cert.id},
            ],
            "properties": {"category": "image", "files": [{"uri": image, "type": "image/webp"}] if image else []},
        }

    if settings.frontend_dir:
        app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
    return app


def _design_or_404(registrar: Registrar, design_id: str) -> Design:
    design = registrar.store.get_design(design_id)
    if design is None:
        raise HTTPException(404, "design not found")
    return design


async def _spool(upload: UploadFile, tmp_dir: Path, limit: int) -> tuple[str, int, Path]:
    """Copy the upload to a temp file while hashing it, enforcing the size limit."""
    digest = hashlib.sha256()
    size = 0
    fd, name = tempfile.mkstemp(dir=tmp_dir)
    path = Path(name)
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := await upload.read(CHUNK):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, f"files are limited to {limit // (1024 * 1024)} MB")
                digest.update(chunk)
                out.write(chunk)
        if size == 0:
            raise HTTPException(422, "the file is empty")
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return digest.hexdigest(), size, path


def _line(event: dict[str, Any]) -> bytes:
    return (json.dumps(event, ensure_ascii=False) + "\n").encode()


async def _reconcile_forever(registrar: Registrar, interval: float = 120.0) -> None:
    while True:
        try:
            await registrar.recover()
        except Exception:  # noqa: BLE001 - keep the loop alive
            log.exception("reconciliation pass failed")
        await asyncio.sleep(interval)


def app_factory() -> FastAPI:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return create_app()

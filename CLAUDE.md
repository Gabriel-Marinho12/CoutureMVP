# Couture: agent harness

> **DIRECTION CHANGE (2026-11-03): read `SPEC.md` first.** Couture is now
> primarily a **luxury clothing store** for independent designers, in the
> Brazilian market, fully custom-built. IP protection of the designer's art is
> a supporting feature. Brand consulting and the Solana registry and
> certificates move to phase 2. Where §1 below or `PRODUCT.md` conflicts with
> `SPEC.md`, SPEC.md wins until they are rewritten. The security rules in
> §3 still apply in full.

Read this whole file before changing code. Sections 3 to 5 are binding rules,
not suggestions. Each rule exists because a security audit (2026-11-02) found
the corresponding bug in this codebase. Breaking a rule re-opens a known
vulnerability.

---

## 1. Business context (short)

Couture is B2B SaaS + Solana infrastructure that protects independent fashion
designers' IP and authenticates physical garments.

- **Designers:** an upload is hashed (SHA-256) and the hash is written on-chain with
  SPL Memo v2. This is an **immutable timestamp of possession, NOT proof of
  legal authorship.** Never write copy, comments or features that claim otherwise.
- **Portfolio display:** the HTML5 Canvas reassembles a server-scrambled sprite.
  This is **friction against casual saving and generic scrapers only.** See §6:
  a script defeats it. Never market or document it as strong protection.
- **Buyers:** each sale mints a compressed NFT (Metaplex Bubblegum V2) as a
  certificate of authenticity.
- **Revenue:** subscriptions plus a commission per certified sale. Every mint
  costs platform SOL and one Merkle-tree leaf, so **mints are a spend, guard them.**
- **Planned:** NFC tags signed by the verified designer, KYC of designers,
  Arweave for metadata, and LangChain DMCA drafting.

Current state: hackathon PoC turned into an MVP. A FastAPI backend lives in
`backend/app/` and a static frontend in `frontend/`, which is GitHub Pages
compatible. `frontend_poc/` is the original PoC. The old
`solana_ip_registry.py` no longer exists.

## 2. Code map

| Path | Role |
|---|---|
| `vitrine/` | **Phase 0 storefront (current focus).** Edit `catalog.json`, run `python vitrine/build.py` (stdlib only), output in `vitrine/site/`. `--strict` fails while example content, missing photos, or missing WhatsApp, CNPJ or e-mail would block publishing. **Fluidity is a requirement (luxury site):** keep the cross-document view transitions, the speculation-rules prerender, the generated versioned service worker (`site/sw.js`, which precaches every page) and the `?v=` content hashes on assets. The nav indicator in `assets/site.js` follows clicks and the section in view: new home sections that have a nav item need `id` plus `data-section` on that item. Load page-specific JS only on its page. Test with `prefers-reduced-motion` too. |
| `backend/app/main.py` | HTTP API, `WriteGuard` middleware, auth (`principal_for`, `require_principal`), input cleaning |
| `backend/app/config.py` | Settings from env/.env, `parse_api_keys` (key → principal) |
| `backend/app/registration.py` | Registration jobs, certificate issuance rules, public views, recovery |
| `backend/app/storage.py` | SQLite (+ `MIGRATIONS`) and files (originals by hash, previews, thumbnails) |
| `backend/app/imaging.py` | Preview / scrambled sprite / thumbnail from **untrusted** uploads |
| `backend/app/solana/rpc.py` | Resilient JSON-RPC; never double-submits |
| `backend/app/solana/memo.py` | Memo registry (only hash + server id go on-chain) |
| `backend/app/solana/cnft.py` + `backend/metaplex/cnft.mjs` | Node sidecar for Bubblegum (third-party npm code) |
| `backend/tests/` | pytest; `test_api.py` has the security regression tests |

Run tests from `backend/`: `pip install -r ../requirements-dev.txt` then `python -m pytest -q`.

## 3. Security rules (binding)

### 3.1 Authentication and authorization
- **Every access key maps to a principal** (designer or studio):
  `COUTURE_API_KEYS=atelier-a=<key>,atelier-b=<key>`. Never go back to a flat
  list of interchangeable keys.
- **Every write records who did it.** `designs.owner` and `certificates.issued_by`
  hold the principal. New write tables must have the same kind of column.
- **Ownership is checked at the last decision point**, inside `Registrar`, not
  only in the route. Only the design's owner may issue its certificates
  (`design_owned_by`). Another principal can never take over a hash, even a
  `failed` one (`Store.claim_design`).
- Legacy rows with `owner IS NULL` belong to the `default` principal. Do not
  treat NULL as "anyone".
- Compare secrets as **bytes** with `hmac.compare_digest` and check every key
  without returning early. A `str` compare raises on non-ASCII and returns 500.
- **Every new write endpoint must be `POST` under `/api/`**, so `WriteGuard`
  covers it, and must take `principal: Principal`.
- **FastAPI pitfall:** with `from __future__ import annotations`, `Annotated`
  dependency aliases must live at module level. If you define one inside
  `create_app()`, FastAPI silently treats it as a query parameter and returns
  422. This happened during the fix.

### 3.2 Request bodies and resource limits
- FastAPI reads multipart/JSON bodies **before** it resolves dependencies, so
  `Depends(auth)` alone does not stop an unauthenticated client from
  streaming a huge body to disk.
- `WriteGuard` (ASGI, runs before the body is read) is the control. For every
  POST under `/api/` it checks the key, **requires `Content-Length`** (411
  for chunked bodies), and caps it: the upload limit for `/api/designs`, 64 KB
  for everything else.
- Do not remove it, do not bypass it with GET-with-body, and keep it inside
  `CORSMiddleware` (add it first) so rejections still carry CORS headers.
- Every endpoint that spends money or tree capacity must have **idempotency +
  quotas**. Certificates need a unique `order_id` per design
  (`UNIQUE(design_id, order_id)`). A replay returns the same certificate with
  HTTP 200 and mints nothing. A different wallet for the same order gets 409.
  An order whose certificate **failed** (nothing landed on-chain) may be
  retried with the same `order_id`. The frontend must send a **stable**
  order reference (typed by the designer or taken from a checkout), never a
  random id per click, because a random id defeats idempotency. Access keys
  are checked with `GET /api/session`, which has no side effects.
  Spend is capped by `COUTURE_CERT_LIMIT_PER_HOUR` per principal and
  `COUTURE_MAX_CERTS_PER_DESIGN`.
- Public endpoints must not do expensive work per request. Cache derived
  bytes on disk, as `thumbnail_path` does.
- Per-IP rate limiting is expected at the reverse proxy: `/view` still encodes
  a sprite on every request. Never deploy without a proxy that applies
  `limit_req` and `client_max_body_size`.

### 3.3 Untrusted files and text
- Uploads are hostile input. `imaging.make_preview` must never raise, because
  any decoder error has to mean "no preview" and not a 500 after the design
  was claimed.
- `Image.MAX_IMAGE_PIXELS` stays at 40 MP or below, with
  `DecompressionBombWarning` promoted to an error. Measure memory before
  raising it.
- Originals are stored only under their **server-computed** hash and are
  never served. File paths come only from server values (sha256, generated
  ids), never from `filename` or other client input.
- Free text (`title`, `designer`, `filename`) goes through `clean_text`:
  NFC normalisation, removal of control and bidi/format characters, and a
  length bound.
- Text sent on-chain must fit protocol limits. The cNFT name is at most 32
  bytes UTF-8 (`fit_utf8`). Memos carry only the hash and server ids, never
  personal data.
- SQL is always parameterised. Dynamic column names (`update_*`) may come
  only from internal code, never from request data.

### 3.4 Secrets and information exposure
- **Raw exception text never leaves the API.** `error` (it can contain RPC
  URLs with provider API keys, or sidecar stderr), `owner` and `issued_by` are
  stripped in `design_view` / `certificate_view`
  (`PRIVATE_DESIGN_FIELDS`, `PRIVATE_CERT_FIELDS`).
- New response fields go through these views. Return `HTTPException` details
  that are fixed strings and send the details to `log`.
- **Subprocesses get an env allowlist** (`cnft.sidecar_env`), never
  `os.environ`. The Node sidecar runs third-party npm code. Add a variable
  only if `cnft.mjs` reads it.
- Secrets (`.env`, `backend/.secrets/`, keypairs, `backend/data/`) are
  gitignored. Never commit them, never log them, and never put them in test
  fixtures. Keys must be at least 16 printable ASCII characters
  (`parse_api_keys` enforces this).
- `/api/docs` and `/api/openapi.json` are disabled on mainnet-beta, and
  mainnet refuses to start without `COUTURE_API_KEYS`.

### 3.5 On-chain correctness
- Never re-send a transaction whose outcome is unknown. Use
  `ConfirmationUnknown` and reconcile instead (see `rpc.py` and `cnft.mjs`).
- `Registrar.recover()` must not touch work that is still live: it skips
  in-memory jobs and `pending` rows younger than `SETTLE_AFTER_SECONDS` that
  have no signature.
- Schema changes are made only through `storage.MIGRATIONS` (nullable
  `ALTER TABLE ADD COLUMN`) plus `POST_MIGRATION` for indexes. Production
  databases already exist.

## 4. Checklist before you finish any backend change

1. Does the change add or alter a write path? Then confirm it is a POST under
   `/api/`, takes `Principal`, checks ownership in `Registrar`, and that money
   or capacity spend is idempotent and capped.
2. Does a new response field expose `error`, owner data or raw exception text?
   It must go through the views.
3. Does any new input reach a file path, SQL identifier, subprocess, on-chain
   payload or wallet-visible metadata? Validate it and bound it.
4. Can a public endpoint be called in a loop? It must be cheap or cached.
5. **Add a regression test** in `backend/tests/test_api.py` for every security
   rule you touch. The `# ---- regression tests for the security audit`
   section shows the pattern, and its tests must keep passing.
6. Run `python -m pytest -q` from `backend/` and report the real result.
7. If the API contract changed (e.g. a new required field), update
   `frontend/assets/app.js` and `backend/.env.example` in the same change.

## 5. Agent working rules

- If a stated path does not exist (e.g. "audit `app/`" when the code is in
  `backend/app/`), say so and confirm the real target. Do not guess silently.
- Security reviews: name the trust boundary crossed and the concrete impact.
  Separate confirmed findings from "needs validation". Do not present
  best-practice gaps as vulnerabilities. Do not probe deployed endpoints or
  spend real SOL; use the fakes in `tests/`.
- Do not claim that the Canvas obfuscation, watermarking or on-chain hashes
  prove authorship or stop determined copying.
- Frontend anti-copy guards (`CoutureCanvas.installGuards`) apply **only to
  the viewer stage, only while the viewer is open**, and are removed on
  close. Never block copy, the context menu or shortcuts page-wide, and never
  write to the clipboard. People must be able to copy fingerprints,
  signatures and links. Every irreversible on-chain action in the UI needs an
  explicit review step that says what will happen and on which network.

## 6. Known residual risks (accepted for now, tracked)

- **Canvas scrambling is bypassable:** `/view` returns the sprite and its
  `order` together, and `/thumbnail.webp` is a plain 512 px image. Next step:
  a session challenge before `order`, per-IP limits, and a tiled diagonal
  watermark.
- **No identity verification:** a principal's `designer` text is still
  self-declared. KYC (planned) must bind principals to verified identities.
  There is no dispute flow yet when someone registers another person's public
  design first.
- `/api/health` is public and shows the platform wallet balance.
- The commitment is `confirmed`. Consider `finalized` before treating a
  registration as legal-grade evidence.
- Certificate metadata is served from this API (mutable). Arweave is planned.

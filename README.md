# Couture - Luxury IP Protection & Brand Ecosystem

Couture is a B2B SaaS platform and Web3 infrastructure designed to protect luxury fashion brands and independent designers from digital design theft, while providing the launchpad to build sovereign brands.

## The Problem
The luxury industry loses billions annually to IP theft. Fast-fashion manufacturers scrape high-resolution designs from independent creators, pushing knock-offs to market faster than legal recourse. Traditional IP law is reactive. Independent designers struggle to monetize without surrendering their IP to established labels, and secondary markets suffer from a lack of indisputable provenance.

## What the MVP does

1. **Register:** a designer uploads a design. It is fingerprinted with SHA-256 (in the browser and again on the server) and the fingerprint is written to Solana with the SPL Memo program. The interface streams each step live: received, fingerprinted, submitted (with the transaction link), sealed.
2. **Protect:** the collection is rendered on HTML5 canvas from a shuffled tile sprite. No image URL or file reaches the browser. Canvas read-back is disabled, saving/dragging/copying/printing is blocked, the view blurs when the window loses focus, and every view carries a per-session watermark. The original upload never leaves the server.
3. **Verify:** anyone can drop a file (hashed locally, never uploaded) or paste a fingerprint to check it against the registry.
4. **Certify:** on purchase, the brand mints a compressed NFT (Metaplex Bubblegum V2) to the buyer's wallet as a certificate of authenticity linked to the registration.

On-chain memo format: `couture:ip:v1 sha256=<hex> ref=<design id>`. No personal data goes on-chain.

## Repository structure

```
backend/
  app/
    main.py           FastAPI app (API + serves the frontend in development)
    registration.py   registration/certification workflows, crash recovery
    imaging.py        previews, shuffled tile sprites, thumbnails
    storage.py        SQLite records + private file store
    cli.py            operator commands (wallet, airdrop, create-tree, register, reconcile)
    solana/
      rpc.py          resilient JSON-RPC client: failover, backoff, safe rebroadcast
      memo.py         authorship registry (SPL Memo v2)
      cnft.py         certificate minting, driving the Metaplex sidecar
      wallet.py       platform fee-payer keypair
  metaplex/cnft.mjs   Bubblegum V2 sidecar (official Metaplex JS SDK)
  tests/
frontend/             static site (GitHub Pages compatible)
docs/architecture.md
```

## Running locally

Requirements: Python 3.12+, Node.js 20+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
(cd backend/metaplex && npm ci)

cd backend
cp .env.example .env
../.venv/bin/python -m app.cli wallet --create   # prints the platform wallet address
```

### Option A: local validator (recommended for development)

Unlimited SOL and no faucet limits. Install the Solana CLI once (`sh -c "$(curl -sSfL https://release.anza.xyz/stable/install)"`), then in one terminal:

```bash
backend/scripts/localnet.sh        # clones the Metaplex programs from devnet; --reset wipes the chain
```

and in `backend/.env` set `SOLANA_CLUSTER=localnet` and `COUTURE_DATA_DIR=data/localnet`. Then:

```bash
../.venv/bin/python -m app.cli airdrop 100
../.venv/bin/python -m app.cli create-tree
../.venv/bin/uvicorn app.main:app_factory --factory --port 8000
```

Explorer links open explorer.solana.com in custom-cluster mode, pointed at your local node.

### Option B: devnet

Fund the wallet with devnet SOL at https://faucet.solana.com (the RPC airdrop and the faucet are rate-limited per IP/account), then:

```bash
../.venv/bin/python -m app.cli wallet            # confirm the balance
../.venv/bin/python -m app.cli create-tree       # once, enables certificates (~0.25 SOL of rent on devnet)
../.venv/bin/uvicorn app.main:app_factory --factory --port 8000
```

Open http://localhost:8000. The API reference is at http://localhost:8000/api/docs.

Tests: `cd backend && ../.venv/bin/python -m pytest`.

## Deployment notes

- **Frontend:** GitHub Pages serves `frontend/` (the repository root and the old `frontend_poc/` redirect there). Without a backend it runs in demo mode. Point `frontend/config.js` at a deployed API and add the Pages origin to `COUTURE_CORS_ORIGINS`.
- **Backend:** any host that runs Python and Node (a container, Fly.io, Render, a VM). Persist `COUTURE_DATA_DIR`, inject the wallet via `COUTURE_KEYPAIR`, set `COUTURE_API_KEYS`, and list a dedicated RPC provider first in `SOLANA_RPC_URLS`.
- **Mainnet:** set `SOLANA_CLUSTER=mainnet-beta`. The server refuses to start there without access keys.

## Not in this MVP yet

Arweave storage for encrypted originals and certificate metadata (metadata is currently served by the API), and LangChain-drafted DMCA notices. Both are planned on top of the existing registry records.

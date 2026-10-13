# CoutureMVP - System Architecture

## 1. Data flow

```text
[ Designer ] ── upload (multipart) ──▶ POST /api/designs
                                          │  stream to disk + SHA-256 (incremental)
                                          │  claim record by hash (duplicates return the original)
                                          │  preview: downscale + watermark (original stays private)
                                          ▼
                                   background job ──▶ SPL Memo v2 transaction ──▶ Solana
                                          │                "couture:ip:v1 sha256=… ref=…"
                                          ▼
                     NDJSON events streamed back: received → hashed → submitting
                                                  → submitted (signature) → confirmed

[ Visitor ] ── GET /api/designs/{id}/view ──▶ shuffled tile sprite + order ──▶ canvas reassembly

[ Brand ] ── POST /api/designs/{id}/certificates {owner} ──▶ Node sidecar ──▶ Bubblegum V2 mintV2
                                                                              (compressed NFT to buyer)
```

## 2. Solana robustness

`app/solana/rpc.py` and `backend/metaplex/cnft.mjs` follow the same rules:

- **Failover:** every call walks the configured endpoints, sticking to the last healthy one.
- **Retries:** timeouts, connection errors, HTTP 429/5xx and node-health RPC codes are retried with exponential backoff and jitter (honouring `Retry-After`). Request errors are not retried.
- **No double submission:** a signed transaction is rebroadcast unchanged (same signature, idempotent) until it is confirmed or its blockhash has provably expired (block height past `lastValidBlockHeight`, plus a final status check). Only then is it rebuilt with a fresh blockhash.
- **Classified failures:** insufficient funds and program errors are permanent; an expired-without-landing transaction is safe to retry; a broadcast whose outcome is unknown is recorded as `unconfirmed` with its signature and settled later by the reconciler (every 2 minutes and at startup), never resubmitted.
- **Decoupled jobs:** registration runs in a background task, so a closed browser tab does not abort it.

## 3. Why a Node sidecar for Metaplex

Metaplex maintains official SDKs only for JavaScript and Rust. Bubblegum V2 instructions, Merkle tree sizing and leaf parsing are taken from `@metaplex-foundation/mpl-bubblegum` instead of being re-implemented in Python. The Python backend calls `node cnft.mjs <create-tree|mint>` with JSON in and one JSON line out, and adds its own retries for failures the sidecar marks as safe.

## 4. Front-end protection layers

1. Originals never leave the server. Views are downscaled (max 1600 px) with a burned-in fingerprint mark.
2. Each view is a freshly shuffled 8×8 tile sprite. Each tile carries a 2 px extruded border, so lossy compression cannot bleed between tiles. It is decoded into an `ImageBitmap`, never an `<img>` or URL.
3. Protected canvases refuse `toDataURL`, `toBlob`, `captureStream` and `getImageData`.
4. Context menu, drag, copy, select, save/print/view-source shortcuts and printing are blocked. PrintScreen clears the clipboard.
5. The viewer veils itself when the window loses focus or the tab is hidden.
6. A diagonal watermark with the viewer's session id is drawn over every rendering.

None of this can stop a screenshot. Its purpose is to defeat casual saving and generic scrapers. Proof of authorship comes from the on-chain registration.

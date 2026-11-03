# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Primary: the independent fashion designer.** They work alone or in a small
studio, have no legal team, and publish portfolio work that fast-fashion
manufacturers can scrape and copy. Their jobs on Couture:

1. Seal a new design the moment it exists (upload → SHA-256 → Solana).
2. Show the collection publicly without handing out saveable files.
3. Issue a certificate of authenticity to a buyer when a piece sells.

**Secondary: buyers and resellers.** They verify a file or fingerprint against
the registry and hold the certificate (a cNFT) for a garment they bought. They
need no account and no access key.

B2B brand/studio teams are part of the business model (subscriptions), but they
are not the primary user of the current interface.

## Product Purpose

Couture gives independent designers an immediate, inexpensive and verifiable
record that they possessed a design at a given moment, a way to display their
work with friction against casual copying, and a link between a sold garment
and an on-chain certificate.

Success means a designer can seal a design in under a minute, without crypto
knowledge, and later point anyone to a public, independent proof of it.

## Positioning

- An **immutable on-chain timestamp of possession** (SPL Memo on Solana) that
  is created automatically at upload, carries no personal data and can be
  verified by anyone without trusting Couture.
- It is **not proof of legal authorship.** It strengthens a designer's
  position in a dispute when combined with off-chain evidence (dated sketches,
  files). Every surface must keep this distinction.

## Operating Context

- **Studio:** register (live stream of steps: received → fingerprinted →
  submitted with transaction link → sealed), the protected collection, and
  certificate issuance (needs an access key).
- **Public:** verify by dropping a file (hashed locally, never uploaded) or
  pasting a fingerprint, and view certificates and metadata from wallets and
  explorers.
- Proof lives on Solana explorers (devnet today). Certificates live in buyers'
  wallets.

## Capabilities and Constraints

- **Stack:** static frontend in `frontend/` (plain HTML/CSS/JS, GitHub Pages
  compatible) and a FastAPI backend with a Node/Metaplex sidecar in `backend/`.
  Security rules are in `CLAUDE.md` and are binding.
- **Protected display:** the HTML5 Canvas reassembles a server-scrambled tile
  sprite, with a watermark, blocked saving and blur on focus loss. This is
  **friction against casual saving and generic scrapers, not protection
  against screenshots or a determined scraper.** Never describe it as
  "unstealable".
- **Certificates:** compressed NFTs (Metaplex Bubblegum V2), one per order
  (`order_id`). Only the designer who registered a design can certify it.
- **Network:** Solana devnet today. Mainnet is not live.
- **Languages:** the product must support **English and Portuguese**. The
  current UI is English-only, so i18n is not yet implemented.
- **Planned, not built** (never present as available): designer KYC, NFC tags
  signed by the designer, Arweave storage, AI-drafted DMCA notices, and a
  dispute flow.

## Brand Commitments

- Name: **Couture**. The current site uses a wordmark with a hairline monogram
  "C" (`frontend/`).
- Voice: precise and restrained. It claims only what the technology proves,
  and never overstates legal or anti-copy guarantees.

## Evidence on Hand

- **Usable:** real transactions on Solana devnet (explorer links produced by the
  registry) as live, verifiable proof.
- **Do not use:** the hackathon submission and the early validation with
  designers are not cleared for public copy. There are no testimonials,
  customer logos, press, user counts, pricing or benchmarks, and none may be
  fabricated.

## Product Principles

1. **Claim only what is provable.** A timestamp is not authorship, and
   friction is not protection.
2. **Crypto stays invisible to the designer.** No wallet is required to seal a
   design, and on-chain proof appears as a plain, checkable link.
3. **Verification is open to anyone.** No account is needed, and files are
   hashed locally and never uploaded to verify.
4. **The original never leaves the server.** Only derivatives are shown.
5. **Every irreversible or paid action is explicit.** Sealing and certifying
   say what will happen on-chain before it happens.

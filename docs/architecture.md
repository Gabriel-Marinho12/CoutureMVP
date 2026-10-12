# CoutureMVP - System Architecture

This document outlines the theoretical architecture and data flow for the CoutureMVP platform, bridging Web2 e-commerce with Web3 IP protection.

## 1. Core Architecture Flow
```text

[ Designer ] 
    │
    ▼ (Uploads High-Res Design)
┌──────────────────────┐
│ CoutureMVP Backend   │ ──(1) Hash Generation (SHA-256)
│ (Python / Node.js)   │ ──(2) Encrypted Storage (Arweave)
└──────────┬───────────┘
           │
           ▼ (Mints cNFT via API)
╔══════════════════════╗
║   SOLANA BLOCKCHAIN  ║  <-- Immutable IP Timestamp registered!
║   (cNFT / Metaplex)  ║
╚══════════════════════╝
```
## 2. Platform Modules

### Module A: IP Registration (The Backend)
When a luxury brand or designer uploads a new sketch or 3D model:
1. The backend script intercepts the file and generates a unique cryptographic hash (SHA-256).
2. The system triggers a Solana Smart Contract (Program) to mint a Compressed NFT (cNFT).
3. The file's Hash and the Timestamp are permanently recorded on the Solana ledger, serving as indisputable proof of authorship for DMCA takedowns or legal disputes.

### Module B: Visual Obfuscation (The Frontend)
When a general user or potential scraper visits the storefront:
1. The raw high-resolution image is never sent directly via standard tags.
2. The image is rendered dynamically inside an HTML5 canvas element.
3. Native browser functions (Right-click context menu, drag-and-drop) are disabled. 
4. Future implementation: Image tiling and dynamic WebGL rendering for 3D garments to completely eliminate high-res source file scraping.

### Module C: Digital Twin (The Consumer Verification)
When a verified customer purchases the physical garment:
1. The physical item is shipped.

2. The corresponding cNFT (containing the IP hash and authenticity metadata) is transferred to the customer's Solana Wallet (e.g., Phantom).
3. The customer now holds an unforgeable digital certificate guaranteeing the physical item's authenticity and preserving its secondary market value.

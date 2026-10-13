# Couture - Luxury IP Protection & Brand Ecosystem

Couture is a B2B SaaS platform and Web3 infrastructure designed to protect luxury fashion brands and independent designers from digital design theft, while providing the launchpad to build sovereign brands.

## The Problem
The luxury industry loses billions annually to IP theft. Fast-fashion manufacturers scrape high-resolution designs from independent creators, pushing knock-offs to market faster than legal recourse. Traditional IP law is reactive. Independent designers struggle to monetize without surrendering their IP to established labels, and secondary markets suffer from a lack of indisputable provenance.

## The Couture Architecture
We merge advanced Web2 front-end defense with Web3 immutability:

1. **Frontend Obfuscation:** High-resolution assets are rendered dynamically via HTML5 Canvas with invisible overlay layers, disabling native browser interactions and preventing automated scraping.
2. **Immutable Timestamping:** Every uploaded design is hashed (SHA-256) and registered directly on the Solana blockchain (SPL Memo / cNFT integration), providing irrefutable, decentralized proof of authorship.
3. **Digital Twins:** Upon physical purchase, the buyer receives a Compressed NFT (cNFT) serving as a digital certificate of authenticity, preserving resale value.

## Hackathon Proof of Concept (PoC)
This repository contains the functional architectural PoC built during the Colosseum hackathon timeframe.

### Repository Structure
* `/frontend`: Contains the `index.html` live demonstration of our front-end obfuscation rendering a luxury garment in an isolated Canvas environment.
* `/backend`: Contains the `solana_ip_registry.py` script. This is a **live network integration**, not a mock. It generates a cryptographic hash of a design file and interacts with the Solana Devnet via the SPL Memo Program to permanently etch the IP timestamp on-chain.
* `/docs`: Contains `architecture.md` mapping the data flow.

### Running the Live Integration

**1. Setup Environment**
```bash
pip install -r requirements.txt

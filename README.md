# Couture
A luxury fashion platform combining frontend visual protection with Solana-based cNFTs to register design authorship and issue unforgeable certificates of authenticity.

## The Problem
Digital design theft and physical counterfeiting in the luxury fashion industry.

## The Solution
1. **Frontend Protection**: High-res images are rendered using HTML5 Canvas with right-click and drag functionalities disabled to prevent simple scraping.
2. **Backend/Blockchain**: An automated Python script hashes the original design and records the timestamp on the Solana blockchain (Devnet) as an immutable proof of authorship.

## How to run this Proof of Concept (PoC)
### Frontend
1. Go to the `frontend_poc` folder.
2. Open `index.html` in your browser.
3. Try to right-click or drag the image to see the protection in action.

### Backend (Solana Hash Minter)
1. Navigate to `backend_poc`.
2. Install dependencies: `pip install solana`
3. Run the hash generator: `python hash_generator.py`
4. Run the Solana minter: `python solana_minter.py`

---
target: ./frontend_poc (resolved to frontend/)
total_score: 20
max_score: 40
na_heuristics: 
p0_count: 1
p1_count: 4
target_identity: "file:C:\\Users\\gabri\\VS_code\\.vscode\\Couture\\CoutureMVP\\frontend\\index.html"
target_fingerprint: "sha256:2f3d8d7c58a30bf333cfadfa2cc74fc9bde0767fe259d35ffe203ad4b8ece175"
target_path: "C:\\Users\\gabri\\VS_code\\.vscode\\Couture\\CoutureMVP\\frontend\\index.html"
timestamp: 2026-11-03T06-31-50Z
slug: frontend-index-html
---
Method: dual-agent (A: design review · B: detector). Target frontend/ (frontend_poc redirects there). No browser: A from source, B CLI detector only.

## Design Health Score: 20/40 (Acceptable)
H1 2 (no loading/offline states; seal panel may land off-screen) · H2 2 (crypto jargon everywhere) · H3 1 (global copy/contextmenu/shortcut guards, clipboard wipe; no review before certify) · H4 2 (state vocabulary drift; "Sealed" on pending; truncated signatures) · H5 2 (no confirmation; fresh order_id per submit -> double mint; no client 50MB check) · H6 3 · H7 2 · H8 3 · H9 1 (raw error strings; silent empty gallery offline) · H10 2

## Design Specificity
Interaction is product-specific (streamed timeline + client/server hash match, local verify, veil). Skin is generic luxury-editorial, addressed to a maison rather than the independent designer; landing-page composition puts the hero before the primary job.
Detector: 19 findings — 14 design-system-font-size (5x 10px labels drift from 11px label token; 7x 13-14px undocumented small-body step), 3 undersized-ui-text (10px field labels), 2 wide-tracking (borderline FP). LLM-only: contrast failures (Ink Mute 2.92 on Paper, bronze small text 4.28/3.88).

## Priority Issues
- [P0] Certify blocked on a new device (key only saved in Register submit, app.js:305-307); certify form shown to all visitors. harden/clarify
- [P1] Copy contradicts PRODUCT.md (authorship, "provably yours", permanent on devnet, NFC binding, "Registered original", Designer as fact). clarify
- [P1] No confirmation for irreversible on-chain actions; random order_id per submit allows double mint (app.js:242). harden
- [P1] Global protection guards break copying proofs/links, clipboard wipe (app.js:221, viewer.js:108-128). harden
- [P1] Accessibility: contrast, invisible drop-zone focus, no modal focus trap/return, no live announcements, no h1, 10px labels. audit -> polish

## Persona Red Flags
Jordan: Solana/devnet/NFT jargon; no "keep this exact file" in Register; no route to get a key.
Sam: invisible focus on drops, modal escapes, silent timeline, static document.title, colour-only status.
Casey: ~30px nav, ~14px Replace, form below fold, "Drop" copy, close top-right.
Marina (indie designer): lands on hero, retypes name, no batch, no receipt, endless unconfirmed pulse, celebratory panel for someone else's duplicate.

## Minor
Hard-coded EN strings (i18n), pending shown Sealed, wallet balance in tooltip, demo mode ends in error, button>div markup, cursor:progress on all disabled.

## Questions
Home = seal action instead of gallery? Hide "Solana" until the receipt? Verify from certificate/QR first, file hash as forensic fallback?

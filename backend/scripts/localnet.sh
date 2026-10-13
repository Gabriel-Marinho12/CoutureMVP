#!/usr/bin/env bash
# Local Solana cluster for development: unlimited SOL, no faucet limits.
# Clones the Metaplex programs certificates need from devnet on first start.
#   scripts/localnet.sh          keep the existing ledger (tree, registrations)
#   scripts/localnet.sh --reset  start from an empty chain
# Ports stay clear of the API on :8000 (RPC on :8899, internal ports 8900-8999).
set -euo pipefail
cd "$(dirname "$0")/.."
PATH="$HOME/.local/share/solana/install/active_release/bin:$PATH"

exec solana-test-validator \
  --ledger .localnet \
  --quiet \
  --gossip-port 8900 \
  --dynamic-port-range 8901-8999 \
  --url https://api.devnet.solana.com \
  --clone-upgradeable-program BGUMAp9Gq7iTEuizy4pqaxsTyUCBK68MDfK752saRPUY \
  --clone-upgradeable-program mcmt6YrQEMKw8Mw43FmpRLmf7BqRnFMKmAcbxE3xkAW \
  --clone-upgradeable-program mnoopTCrg4p8ry25e4bcWA9XZjbNjMTfgYVGGEdRsf3 \
  --clone-upgradeable-program CoREENxT6tW1HoK8ypY1SxRMZTcVPm7R94rH4PZNhX7d \
  "$@"

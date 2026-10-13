#!/usr/bin/env bash
# Local Solana cluster for development: unlimited SOL, no faucet limits.
# Clones the Metaplex programs certificates need from devnet on first start.
#   scripts/localnet.sh          keep the existing ledger (tree, registrations)
#   scripts/localnet.sh --reset  start from an empty chain
# Ports stay clear of the API on :8000 (RPC on :8899, internal ports 8900-8999).
#
# The ledger grows ~100 MB per minute even when idle, and --limit-ledger-size
# does not bound it on the test validator (left running, it once filled the
# disk). A watchdog stops the validator once the ledger passes LEDGER_MAX_MB
# (default 2048); restart with --reset to reclaim the space.
set -euo pipefail
cd "$(dirname "$0")/.."
PATH="$HOME/.local/share/solana/install/active_release/bin:$PATH"
MAX_MB="${LEDGER_MAX_MB:-2048}"

solana-test-validator \
  --ledger .localnet \
  --quiet \
  --gossip-port 8900 \
  --dynamic-port-range 8901-8999 \
  --url https://api.devnet.solana.com \
  --clone-upgradeable-program BGUMAp9Gq7iTEuizy4pqaxsTyUCBK68MDfK752saRPUY \
  --clone-upgradeable-program mcmt6YrQEMKw8Mw43FmpRLmf7BqRnFMKmAcbxE3xkAW \
  --clone-upgradeable-program mnoopTCrg4p8ry25e4bcWA9XZjbNjMTfgYVGGEdRsf3 \
  --clone-upgradeable-program CoREENxT6tW1HoK8ypY1SxRMZTcVPm7R94rH4PZNhX7d \
  "$@" &
validator=$!
trap 'kill "$validator" 2>/dev/null || true' INT TERM EXIT

while kill -0 "$validator" 2>/dev/null; do
  sleep 30
  size=$(du -sm .localnet 2>/dev/null | cut -f1)
  if [ "${size:-0}" -gt "$MAX_MB" ]; then
    echo "localnet: ledger reached ${size} MB (limit ${MAX_MB} MB), stopping. Restart with --reset." >&2
    kill "$validator"
  fi
done
wait "$validator" || true

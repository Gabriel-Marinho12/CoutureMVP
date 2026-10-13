"""Operator commands.

  python -m app.cli wallet [--create]   show (or create) the platform wallet and its balance
  python -m app.cli airdrop [SOL]       request devnet/testnet SOL for the platform wallet
  python -m app.cli create-tree         create the Bubblegum Merkle tree that holds certificates
  python -m app.cli register FILE       register a file from the terminal (no server needed)
  python -m app.cli reconcile           settle records whose on-chain outcome is unknown
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from pathlib import Path

from .config import load_settings
from .registration import Registrar
from .solana import memo
from .solana.cnft import CnftMinter
from .solana.rpc import SolanaError, SolanaRpc
from .solana.wallet import create_keypair, load_keypair
from .storage import Store


async def wallet(args: argparse.Namespace) -> None:
    settings = load_settings()
    if args.create:
        keypair = create_keypair(settings.keypair_path)
        print(f"created {settings.keypair_path}")
    else:
        keypair = load_keypair(settings.keypair_path)
    rpc = SolanaRpc(settings.rpc_urls, commitment=settings.commitment)
    try:
        lamports = await rpc.balance(keypair.pubkey())
    finally:
        await rpc.aclose()
    print(f"address  {keypair.pubkey()}")
    print(f"balance  {lamports / 1e9:.6f} SOL ({settings.cluster})")
    print(f"explorer {settings.explorer_address(str(keypair.pubkey()))}")
    if settings.cluster != "mainnet-beta" and lamports == 0:
        print("\nFund it at https://faucet.solana.com (choose Devnet) or run `python -m app.cli airdrop`.")


async def airdrop(args: argparse.Namespace) -> None:
    settings = load_settings()
    if settings.cluster == "mainnet-beta":
        sys.exit("airdrops only exist on devnet and testnet")
    keypair = load_keypair(settings.keypair_path)
    rpc = SolanaRpc(settings.rpc_urls, commitment=settings.commitment)
    try:
        signature = await rpc.request_airdrop(keypair.pubkey(), int(args.sol * 1e9))
        print(f"airdrop requested: {settings.explorer_tx(signature)}")
    except SolanaError as exc:
        sys.exit(f"airdrop refused ({exc}).\nThe public faucet is rate-limited; use https://faucet.solana.com instead.")
    finally:
        await rpc.aclose()


async def create_tree(args: argparse.Namespace) -> None:
    settings = load_settings()
    store = Store(settings.data_dir)
    existing = settings.merkle_tree or store.get_value("merkle_tree")
    if existing and not args.force:
        sys.exit(f"a tree already exists ({existing}); pass --force to create another")
    result = await CnftMinter(settings).create_tree(
        max_depth=args.depth, max_buffer_size=args.buffer, canopy_depth=args.canopy
    )
    store.set_value("merkle_tree", result.tree)
    print(f"tree     {result.tree} (capacity {result.capacity:,} certificates)")
    print(f"tx       {settings.explorer_tx(result.signature)}")


async def register(args: argparse.Namespace) -> None:
    settings = load_settings()
    data = Path(args.file).read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    rpc = SolanaRpc(settings.rpc_urls, commitment=settings.commitment)
    try:
        print(f"sha256   {sha256}")
        confirmation = await memo.register_hash(
            rpc, load_keypair(settings.keypair_path), sha256, "cli",
            priority_fee_microlamports=settings.priority_fee_microlamports,
            on_broadcast=lambda sig: print(f"sent     {sig}"),
        )
    finally:
        await rpc.aclose()
    print(f"slot     {confirmation.slot}")
    print(f"explorer {settings.explorer_tx(confirmation.signature)}")


async def reconcile(args: argparse.Namespace) -> None:
    settings = load_settings()
    store = Store(settings.data_dir)
    rpc = SolanaRpc(settings.rpc_urls, commitment=settings.commitment)
    try:
        registrar = Registrar(settings, store, rpc, load_keypair(settings.keypair_path), CnftMinter(settings))
        await registrar.recover()
    finally:
        await rpc.aclose()
    for design in store.designs_in("pending", "unconfirmed"):
        print(f"still unsettled: design {design.id} ({design.signature})")
    print("done")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Couture operator commands")
    commands = parser.add_subparsers(dest="command", required=True)

    p = commands.add_parser("wallet", help="show or create the platform wallet")
    p.add_argument("--create", action="store_true")
    p.set_defaults(handler=wallet)

    p = commands.add_parser("airdrop", help="request test SOL")
    p.add_argument("sol", type=float, nargs="?", default=1.0)
    p.set_defaults(handler=airdrop)

    p = commands.add_parser("create-tree", help="create the certificate Merkle tree")
    p.add_argument("--depth", type=int, default=14, help="capacity is 2^depth certificates")
    p.add_argument("--buffer", type=int, default=64, help="concurrent writes per slot")
    p.add_argument("--canopy", type=int, default=0, help="cached proof levels (costs rent)")
    p.add_argument("--force", action="store_true")
    p.set_defaults(handler=create_tree)

    p = commands.add_parser("register", help="register a file's hash on-chain")
    p.add_argument("file")
    p.set_defaults(handler=register)

    p = commands.add_parser("reconcile", help="settle in-flight records")
    p.set_defaults(handler=reconcile)

    args = parser.parse_args()
    asyncio.run(args.handler(args))


if __name__ == "__main__":
    main()

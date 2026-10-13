#!/usr/bin/env node
// Compressed NFT operations through Metaplex Bubblegum V2.
//
// Called by the Python backend (app/solana/cnft.py) as:
//   node cnft.mjs <create-tree|mint> < request.json
// and answers with exactly one JSON line on stdout:
//   {"ok": true, ...result}
//   {"ok": false, "error": {"kind": "retryable"|"permanent"|"unknown", "message", "signature"?}}
//
// "retryable" guarantees nothing landed on-chain; "unknown" means a
// transaction was broadcast and may still land, so it must be reconciled,
// never re-sent. Same submission rules as app/solana/rpc.py.

import { readFileSync } from 'node:fs';
import { createUmi } from '@metaplex-foundation/umi-bundle-defaults';
import {
  createSignerFromKeypair,
  generateSigner,
  keypairIdentity,
  publicKey,
} from '@metaplex-foundation/umi';
import { base58 } from '@metaplex-foundation/umi/serializers';
import {
  createTreeV2,
  mintV2,
  mplBubblegum,
  parseLeafFromMintV2Transaction,
} from '@metaplex-foundation/mpl-bubblegum';

const COMMITMENT = process.env.SOLANA_COMMITMENT || 'confirmed';
const CONFIRM_TIMEOUT_MS = Number(process.env.COUTURE_CONFIRM_TIMEOUT_MS || 90_000);
const REBROADCAST_MS = 2_000;
const MAX_REBUILDS = 3;
const RETRY_ROUNDS = 4;
const RANK = { processed: 0, confirmed: 1, finalized: 2 };

const TRANSIENT = /429|too many requests|fetch failed|ECONNRESET|ECONNREFUSED|ETIMEDOUT|ENOTFOUND|EAI_AGAIN|socket|network|timed? ?out|502|503|504|internal error|node is (behind|unhealthy)/i;
const BLOCKHASH = /blockhash not found|BlockhashNotFound/i;
const FUNDS = /insufficient (funds|lamports)|InsufficientFunds|AttemptToDebitAccountWithNoInsufficientFunds|AccountNotFound/i;

class SidecarError extends Error {
  constructor(kind, message, signature) {
    super(message);
    this.kind = kind;
    this.signature = signature;
  }
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const jitter = (attempt) => Math.min(4000, 250 * 2 ** attempt) * (0.5 + Math.random() / 2);
const describe = (error) => [error?.message, ...(error?.logs || []), error?.cause?.message].filter(Boolean).join(' | ');

function loadSecretKey() {
  const raw = process.env.COUTURE_KEYPAIR ?? readFileSync(process.env.COUTURE_KEYPAIR_PATH, 'utf8');
  const bytes = JSON.parse(raw);
  if (!Array.isArray(bytes) || bytes.length !== 64) throw new SidecarError('permanent', 'invalid platform keypair');
  return Uint8Array.from(bytes);
}

function buildUmis() {
  const urls = (process.env.SOLANA_RPC_URLS || 'https://api.devnet.solana.com').split(',').map((u) => u.trim()).filter(Boolean);
  const secret = loadSecretKey();
  return urls.map((url) => {
    const umi = createUmi(url, { commitment: COMMITMENT }).use(mplBubblegum());
    return umi.use(keypairIdentity(umi.eddsa.createKeypairFromSecretKey(secret)));
  });
}

// Endpoint failover with backoff for transient errors; anything else propagates.
class Network {
  constructor(umis) {
    this.umis = umis;
    this.active = 0;
  }

  get umi() {
    return this.umis[this.active];
  }

  async call(label, fn) {
    let last;
    for (let attempt = 0; attempt < RETRY_ROUNDS; attempt++) {
      for (let offset = 0; offset < this.umis.length; offset++) {
        const index = (this.active + offset) % this.umis.length;
        try {
          const result = await fn(this.umis[index]);
          this.active = index;
          return result;
        } catch (error) {
          if (!TRANSIENT.test(describe(error))) throw error;
          last = error;
          process.stderr.write(`rpc ${label} failed on endpoint ${index}: ${describe(error)}\n`);
        }
      }
      if (attempt + 1 < RETRY_ROUNDS) await sleep(jitter(attempt));
    }
    throw new SidecarError('unavailable', `${label} failed on every endpoint: ${describe(last)}`);
  }

  async status(signature) {
    const [status] = await this.call('getSignatureStatuses', (umi) =>
      umi.rpc.getSignatureStatuses([signature], { searchTransactionHistory: true }));
    return status;
  }

  blockHeight() {
    return this.call('getBlockHeight', (umi) => umi.rpc.call('getBlockHeight', [{ commitment: COMMITMENT }]));
  }

  // makeBuilder() is called again for every rebuild so fresh signers/blockhash apply.
  async sendAndConfirm(makeBuilder) {
    for (let rebuild = 0; rebuild <= MAX_REBUILDS; rebuild++) {
      const latest = await this.call('getLatestBlockhash', (umi) => umi.rpc.getLatestBlockhash({ commitment: COMMITMENT }));
      const tx = await makeBuilder().setBlockhash(latest).buildAndSign(this.umi);
      const signatureBytes = tx.signatures[0];
      const signature = base58.deserialize(signatureBytes)[0];

      try {
        await this.call('sendTransaction', (umi) =>
          umi.rpc.sendTransaction(tx, { skipPreflight: false, preflightCommitment: COMMITMENT, maxRetries: 0 }));
      } catch (error) {
        const text = describe(error);
        if (BLOCKHASH.test(text)) continue;
        if (FUNDS.test(text)) throw new SidecarError('permanent', 'platform wallet has insufficient SOL');
        if (!(error instanceof SidecarError && error.kind === 'unavailable')) {
          throw new SidecarError('permanent', `transaction simulation failed: ${text}`);
        }
        // Unacknowledged broadcast: it may have reached a node, poll to find out.
      }

      try {
        const result = await this.awaitConfirmation(tx, signatureBytes, signature, latest.lastValidBlockHeight);
        if (result) return result;
      } catch (error) {
        if (error instanceof SidecarError && error.kind === 'unavailable') {
          throw new SidecarError('unknown', `lost contact with the network: ${error.message}`, signature);
        }
        throw error;
      }
    }
    throw new SidecarError('retryable', `transaction expired ${MAX_REBUILDS + 1} times without landing`);
  }

  async awaitConfirmation(tx, signatureBytes, signature, lastValidBlockHeight) {
    const deadline = Date.now() + CONFIRM_TIMEOUT_MS;
    for (;;) {
      const status = await this.status(signatureBytes);
      if (status) {
        if (status.error) throw new SidecarError('permanent', `transaction failed: ${JSON.stringify(status.error)}`, signature);
        if (status.commitment && RANK[status.commitment] >= RANK[COMMITMENT]) return { signature, signatureBytes, slot: status.slot };
      } else if ((await this.blockHeight()) > lastValidBlockHeight) {
        if (!(await this.status(signatureBytes))) return null;
        continue;
      }
      if (Date.now() >= deadline) throw new SidecarError('unknown', 'confirmation timed out', signature);
      await sleep(REBROADCAST_MS);
      await this.umi.rpc.sendTransaction(tx, { skipPreflight: true, maxRetries: 0 }).catch(() => {});
    }
  }
}

async function main() {
  const command = process.argv[2];
  const request = JSON.parse(readFileSync(0, 'utf8') || '{}');
  const net = new Network(buildUmis());

  if (command === 'create-tree') return runCreateTree(net, request);
  if (command === 'mint') return runMint(net, request);
  throw new SidecarError('permanent', `unknown command ${command}`);
}

async function runCreateTree(net, request) {
  const maxDepth = request.maxDepth ?? 14;
  const maxBufferSize = request.maxBufferSize ?? 64;
  const canopyDepth = request.canopyDepth ?? 0;
  const merkleTree = generateSigner(net.umi);
  // The tree address is fixed across rebuilds: if a first attempt expired,
  // the account was never created, so the same signer can be reused.
  const builder = await net.call('createTreeV2', (umi) =>
    createTreeV2(umi, { merkleTree, maxDepth, maxBufferSize, canopyDepth, public: false }));
  const confirmation = await net.sendAndConfirm(() => builder);
  return {
    tree: merkleTree.publicKey.toString(),
    signature: confirmation.signature,
    slot: confirmation.slot,
    maxDepth,
    maxBufferSize,
    canopyDepth,
    capacity: 2 ** maxDepth,
  };
}

async function runMint(net, request) {
  const { tree, owner, name, uri, symbol = 'COUTURE', sellerFeeBasisPoints = 0 } = request;
  if (!tree || !owner || !name || !uri) throw new SidecarError('permanent', 'tree, owner, name and uri are required');
  const identity = net.umi.identity.publicKey;
  const metadata = {
    name: name.slice(0, 32),
    symbol: symbol.slice(0, 10),
    uri,
    sellerFeeBasisPoints,
    collection: null,
    creators: [{ address: identity, verified: false, share: 100 }],
  };
  const confirmation = await net.sendAndConfirm(() =>
    mintV2(net.umi, { leafOwner: publicKey(owner), merkleTree: publicKey(tree), metadata }));

  // The asset id comes from the transaction's logs, which RPC nodes may
  // serve a little after confirmation.
  let assetId = null;
  for (let attempt = 0; attempt < 6 && !assetId; attempt++) {
    try {
      const leaf = await parseLeafFromMintV2Transaction(net.umi, confirmation.signatureBytes);
      assetId = leaf.id.toString();
    } catch (error) {
      await sleep(jitter(attempt) + 500);
    }
  }
  return { signature: confirmation.signature, slot: confirmation.slot, assetId };
}

main()
  .then((result) => process.stdout.write(`${JSON.stringify({ ok: true, ...result })}\n`))
  .catch((error) => {
    const kind = error instanceof SidecarError ? (error.kind === 'unavailable' ? 'retryable' : error.kind) : 'permanent';
    process.stderr.write(`${error?.stack || error}\n`);
    process.stdout.write(`${JSON.stringify({ ok: false, error: { kind, message: error?.message || String(error), signature: error?.signature } })}\n`);
    process.exitCode = 1;
  });

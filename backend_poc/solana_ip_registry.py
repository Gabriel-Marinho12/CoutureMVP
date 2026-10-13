import hashlib
import time
import sys
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from solana.transaction import Transaction

def generate_hash(file_data: bytes) -> str:
    return hashlib.sha256(file_data).hexdigest()

def register_ip_on_solana():
    print("Initiating Couture IP Registry Protocol...\n")
    
    try:
        print("[1/5] Connecting to Solana Devnet...")
        client = Client("https://api.devnet.solana.com")
        
        print("[2/5] Generating temporary Keypair for demonstration...")
        wallet = Keypair()
        print(f"      Wallet Address: {wallet.pubkey()}")
        
        print("[3/5] Requesting SOL Airdrop to fund the transaction...")
        client.request_airdrop(wallet.pubkey(), 1_000_000_000) # 1 SOL
        
        # Animação simples de loading no terminal enquanto a rede confirma
        print("      Awaiting network confirmation ", end="")
        for _ in range(15):
            time.sleep(1)
            print(".", end="")
            sys.stdout.flush()
        print(" Done.\n")
        
        print("[4/5] Hashing original high-resolution design file...")
        mock_image_data = b"couture_luxury_garment_design_data_v1_001"
        file_hash = generate_hash(mock_image_data)
        print(f"      SHA-256 Hash: {file_hash}")
        
        print("[5/5] Minting IP Timestamp to Solana ledger (SPL Memo)...")
        memo_program_id = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLXFnc8")
        memo_message = f"Couture Protocol - IP Registry. Immutable Image Hash: {file_hash}"
        
        instruction = Instruction(
            program_id=memo_program_id,
            accounts=[AccountMeta(pubkey=wallet.pubkey(), is_signer=True, is_writable=False)],
            data=memo_message.encode('utf-8')
        )
        
        recent_blockhash = client.get_latest_blockhash().value.blockhash
        txn = Transaction(recent_blockhash=recent_blockhash)
        txn.add(instruction)
        
        response = client.send_transaction(txn, wallet)
        tx_sig = response.value
        
        print("\n" + "="*60)
        print("SUCCESS! INTELLECTUAL PROPERTY REGISTERED IMMUTABLY.")
        print("="*60)
        print(f"Transaction ID: {tx_sig}")
        print(f"Verify on Solana Explorer:")
        print(f"https://explorer.solana.com/tx/{tx_sig}?cluster=devnet")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n[ERROR] Network or runtime failure: {e}")
        print("Please ensure you have internet connection and the Devnet is online.")

if __name__ == "__main__":
    register_ip_on_solana()

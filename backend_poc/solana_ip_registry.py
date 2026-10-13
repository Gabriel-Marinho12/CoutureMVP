import hashlib
import base58
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from solders.message import MessageV0
from solders.transaction import VersionedTransaction


def generate_hash(file_data: bytes) -> str:
    return hashlib.sha256(file_data).hexdigest()


def register_ip_on_solana():
    print("=== Couture IP Registry ===")
    client = Client("https://api.devnet.solana.com")
    wallet = Keypair()

    print("\n[PASSO MANUAL ANTI-BLOQUEIO]")
    print(f"Endereço gerado: {wallet.pubkey()}")
    print("1. Acesse no navegador: https://faucet.solana.com")
    print("2. Cole o endereço acima, selecione 'Devnet' e clique em 'Confirm'.")
    input("3. APERTE ENTER AQUI NO TERMINAL SOMENTE APÓS O SITE CONFIRMAR O ENVIO... ")

    print("\nVerificando saldo na rede...")
    balance = client.get_balance(wallet.pubkey()).value
    if balance == 0:
        print("Erro: A carteira ainda está vazia. O Airdrop pelo site falhou ou não foi confirmado. Tente novamente.")
        return

    print("Saldo confirmado. Registrando autoria na Devnet...")

    mock_image_data = b"couture_luxury_garment_design_data_v1_001"
    file_hash = generate_hash(mock_image_data)

    # BURLANDO O BUG DO SOLDERS: Convertendo o endereço de 42 caracteres direto para bytes
    memo_bytes = base58.b58decode("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLXFnc8")
    memo_program_id = Pubkey(memo_bytes)

    memo_message = f"Couture Protocol - IP Registry. Immutable Image Hash: {file_hash}"

    instruction = Instruction(
        program_id=memo_program_id,
        accounts=[AccountMeta(pubkey=wallet.pubkey(),
                              is_signer=True, is_writable=True)],
        data=memo_message.encode('utf-8')
    )

    recent_blockhash = client.get_latest_blockhash().value.blockhash
    msg = MessageV0.try_compile(
        payer=wallet.pubkey(),
        instructions=[instruction],
        address_lookup_table_accounts=[],
        recent_blockhash=recent_blockhash
    )

    txn = VersionedTransaction(msg, [wallet])
    response = client.send_transaction(txn)

    print("\n================================================")
    print("SUCESSO! PROPRIEDADE INTELECTUAL REGISTRADA.")
    print(f"https://explorer.solana.com/tx/{response.value}?cluster=devnet")
    print("================================================")


if __name__ == "__main__":
    register_ip_on_solana()

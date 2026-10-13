import hashlib
import time
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from solana.transaction import Transaction

def generate_hash(file_data: bytes) -> str:
    """Gera o hash SHA-256 do arquivo (a Prova de Autoria)"""
    return hashlib.sha256(file_data).hexdigest()

def register_ip_on_solana():
    print("1. Conectando à Devnet da Solana...")
    client = Client("https://api.devnet.solana.com")
    
    print("2. Gerando nova carteira (Keypair) para a Couture PoC...")
    # Em produção, a plataforma usaria uma carteira permanente configurada no servidor
    wallet = Keypair()
    print(f"   Endereço Público: {wallet.pubkey()}")
    
    print("3. Solicitando Airdrop de SOL (Devnet) para pagar a taxa...")
    client.request_airdrop(wallet.pubkey(), 1_000_000_000) # 1 SOL
    time.sleep(15) # Aguarda a rede confirmar o saldo
    
    print("4. Gerando a assinatura digital (Hash) do design de luxo...")
    # Simulando a leitura do arquivo de imagem do front-end
    mock_image_data = b"luxury_garment_design_data_v1"
    file_hash = generate_hash(mock_image_data)
    print(f"   Hash SHA-256: {file_hash}")
    
    print("5. Criando transação para gravar o Hash na blockchain (SPL Memo)...")
    # Program ID oficial do SPL Memo na Solana
    memo_program_id = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLXFnc8")
    
    # A mensagem que ficará registrada para sempre (O Carimbo de Tempo)
    memo_message = f"Couture MVP - IP Registry. Image Hash: {file_hash}"
    
    # Monta a instrução do contrato inteligente
    instruction = Instruction(
        program_id=memo_program_id,
        accounts=[AccountMeta(pubkey=wallet.pubkey(), is_signer=True, is_writable=False)],
        data=memo_message.encode('utf-8')
    )
    
    # Pega o blockhash mais recente para validar a transação
    recent_blockhash = client.get_latest_blockhash().value.blockhash
    
    txn = Transaction(recent_blockhash=recent_blockhash)
    txn.add(instruction)
    
    print("6. Assinando e enviando transação para a rede...")
    response = client.send_transaction(txn, wallet)
    
    tx_sig = response.value
    print("\n================================================")
    print("SUCESSO! PROPRIEDADE INTELECTUAL REGISTRADA.")
    print("================================================")
    print(f"ID da Transação: {tx_sig}")
    print(f"Clique para verificar no Explorer (Prova para os Jurados):")
    print(f"https://explorer.solana.com/tx/{tx_sig}?cluster=devnet")

if __name__ == "__main__":
    register_ip_on_solana()

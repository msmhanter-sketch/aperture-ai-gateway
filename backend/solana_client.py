import os
import json
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from anchorpy import Program, Provider, Wallet, Idl
from anchorpy.program.context import Context
from dotenv import load_dotenv

load_dotenv()

class SolanaClient:
    def __init__(self):
        # 1. Подключение
        rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
        self.client = AsyncClient(rpc_url)
        
        # 2. Идентификация программы
        self.program_id = Pubkey.from_string(os.getenv("SOLANA_PROGRAM_ID"))
        
        # 3. Ключ ИИ-Агента (Signer)
        secret = json.loads(os.getenv("BACKEND_PRIVATE_KEY", "[0]*64"))
        self.ai_signer = Keypair.from_bytes(secret)
        self.wallet = Wallet(self.ai_signer)
        
        # 4. Настройка Anchor
        self.provider = Provider(self.client, self.wallet)
        
        idl_path = os.path.join(os.path.dirname(__file__), "aperture_gateway.json")
        try:
            with open(idl_path, 'r', encoding='utf-8') as f:
                self.idl = Idl.from_json(f.read())
            self.program = Program(self.idl, self.program_id, self.provider)
            print(f"🟢 AI ORACLE ONLINE: {self.ai_signer.pubkey()}")
        except Exception as e:
            print(f"🔴 ERROR: IDL Load failed: {e}")
            self.program = None

    async def get_channel_balance(self, user_pubkey_str: str) -> int:
        """
        ЧИТАЕТ РЕАЛЬНЫЙ БАЛАНС ИЗ СМАРТ-КОНТРАКТА (PDA)
        Возвращает баланс в lamports.
        """
        if not self.program:
            return 0

        try:
            user_pubkey = Pubkey.from_string(user_pubkey_str)

            # Находим PDA канала
            channel_pda, _bump = Pubkey.find_program_address(
                [b"channel", bytes(user_pubkey)],
                self.program_id
            )

            try:
                # Читаем стейт аккаунта из блокчейна (имя структуры из Rust)
                # В зависимости от версии AnchorPy, ключ может быть "ChannelState" или "channelState"
                account_name = "ChannelState" if "ChannelState" in self.program.account else "channelState"
                account_data = await self.program.account[account_name].fetch(channel_pda)
                
                # Возвращаем залоченный баланс
                return account_data.balance
            except Exception as fetch_err:
                # Если вылетает ошибка, значит юзер еще не вызвал open_channel
                print(f"⚠️ [ON-CHAIN] Channel not found for {user_pubkey_str}. Needs to deposit first.")
                return 0

        except Exception as e:
            print(f"🔴 [ON-CHAIN] Error reading balance: {e}")
            return 0

    async def update_burn_rate(self, user_pubkey_str: str, new_rate_lamports: int):
        """
        РЕАЛЬНАЯ транзакция в Solana. 
        Меняет стейт смарт-контракта на основе вердикта ИИ.
        """
        if not self.program:
            return False

        try:
            user_pubkey = Pubkey.from_string(user_pubkey_str)

            # Находим PDA аккаунта (он должен уже существовать)
            channel_pda, _bump = Pubkey.find_program_address(
                [b"channel", bytes(user_pubkey)],
                self.program_id
            )

            print(f"📡 [ON-CHAIN] Sending TX to update Burn Rate: {new_rate_lamports} lamports/sec")
            
            # ВЫЗОВ СМАРТ-КОНТРАКТА
            tx_sig = await self.program.rpc["update_burn_rate"](
                new_rate_lamports,
                ctx=Context(
                    accounts={
                        "channel": channel_pda,
                        "ai_agent": self.ai_signer.pubkey(),
                    },
                    signers=[self.ai_signer]
                )
            )

            print(f"✅ [ON-CHAIN] STATE CHANGED! TX: {tx_sig}")
            return str(tx_sig)

        except Exception as e:
            print(f"🔴 [ON-CHAIN] TRANSACTION FAILED: {e}")
            return False

    async def close(self):
        await self.client.close()
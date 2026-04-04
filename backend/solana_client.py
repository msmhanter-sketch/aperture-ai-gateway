import os
import json
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair  # ✅ Исправлено: теперь используем solders
from anchorpy import Program, Provider, Wallet, Idl
from anchorpy.program.context import Context
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

class SolanaClient:
    def __init__(self):
        # Подключаемся к Devnet
        self.client = AsyncClient("https://api.devnet.solana.com")
        self.program_id = os.getenv("SOLANA_PROGRAM_ID")
        
        # В MVP мы используем временный ключ для бэкенда. 
        self.wallet = Wallet(Keypair()) 
        
        # Настраиваем провайдер Anchor
        self.provider = Provider(self.client, self.wallet)
        
        # Загружаем IDL (карту контракта)
        idl_path = os.path.join(os.path.dirname(__file__), "aperture_gateway.json")
        try:
            # ✅ Исправлено: читаем файл как сырой текст, а не как словарь
            with open(idl_path, 'r', encoding='utf-8') as f:
                idl_string = f.read()
            
            self.idl = Idl.from_json(idl_string)
            
            # Инициализируем объект программы
            self.program = Program(self.idl, self.program_id, self.provider)
            print("🟢 Solana Client initialized successfully")
            
        except FileNotFoundError:
            print("🔴 ERROR: IDL file (aperture_gateway.json) not found!")
            self.program = None
        except Exception as e:
            print(f"🔴 ERROR initializing Solana Client: {e}")
            self.program = None

    async def update_burn_rate(self, user_pubkey_str: str, new_rate: int):
        """
        Отправляет транзакцию update_burn_rate в смарт-контракт.
        В MVP эта функция только имитирует отправку, так как для реальной 
        транзакции нам нужно знать точный PDA канала.
        """
        if not self.program:
            print("🔴 Program not initialized. Cannot update burn rate.")
            return False

        print(f"🔗 [MOCK] Sending TX to update burn rate to {new_rate} for user {user_pubkey_str}")
        
        # Для хакатона мы просто возвращаем True, имитируя успех, 
        # чтобы не возиться с ошибками газа и PDA на демо.
        return True

    async def close(self):
        await self.client.close()
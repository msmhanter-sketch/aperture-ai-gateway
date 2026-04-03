from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
import time

# Инициализация сервера
app = FastAPI(title="Aperture AI Gateway")

# Разрешаем запросы от нашего HTML-файла (Убиваем CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Формат данных от фронтенда
class Payload(BaseModel):
    user_wallet: str
    code_or_query: str

# 🧠 Логика ИИ (Оценка алгоритмической сложности)
def ai_evaluate_complexity(payload_text: str) -> int:
    print(f"[AI Agent] Анализирую код: {payload_text[:40]}...")
    
    # Ищем паттерны тяжелых вычислений (O(n^2), внешние API)
    if "while" in payload_text or "for" in payload_text or "matrix" in payload_text:
        score = random.randint(8, 10)
        print(f"[AI Agent] Обнаружена тяжелая нагрузка. Скор: {score}/10")
    elif "print" in payload_text or "hello" in payload_text.lower():
        score = random.randint(1, 3)
        print(f"[AI Agent] Легкий запрос. Скор: {score}/10")
    else:
        score = 5
        print(f"[AI Agent] Стандартная нагрузка. Скор: {score}/10")
        
    return score

# 🔗 Интеграция с Solana
def update_solana_contract(wallet: str, score: int):
    # Расчет цены: базовая цена умножается на уровень сложности ИИ
    new_burn_rate = score * 0.05 
    
    print(f"[Solana CPI] Подписание транзакции для обновления контракта...")
    time.sleep(0.8) # Имитация создания блока (400мс)
    print(f"[Solana CPI] Стейт обновлен! Burn Rate = {new_burn_rate:.2f} USDC/sec")
    
    return round(new_burn_rate, 2)

# 🚀 Главный эндпоинт шлюза
@app.post("/execute")
async def execute_task(req: Payload):
    print("\n" + "="*50)
    print("НОВАЯ ТРАНЗАКЦИЯ")
    
    # 1. Оценка ИИ
    complexity_score = ai_evaluate_complexity(req.code_or_query)
    
    # 2. Изменение цены в смарт-контракте
    burn_rate = update_solana_contract(req.user_wallet, complexity_score)
    
    # 3. Выполнение самого кода юзера (Имитация работы процессора)
    print("[Aperture Compute] Выполнение алгоритмов...")
    time.sleep(2.5) 
    
    # 4. Сброс цены после завершения работы
    print("[Solana CPI] Вычисления завершены. Burn Rate сброшен на 0.")
    print("="*50 + "\n")
    
    return {
        "status": "success",
        "complexity_score": complexity_score,
        "fee_per_second": burn_rate,
        "message": "Compute executed and settled on-chain."
    }
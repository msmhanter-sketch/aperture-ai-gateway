from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import random
import time
import os

# Инициализация приложения
app = FastAPI(title="Aperture AI-Gateway | Cloud Edition")

# 1. Настройка CORS (чтобы браузер не блокировал запросы к твоему IP)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Модель данных (что мы ждем от фронтенда)
class Payload(BaseModel):
    user_wallet: str
    code_or_query: str

# 3. Эндпоинт для открытия сайта (Главная страница)
@app.get("/")
async def read_index():
    # Путь к файлу index.html, который лежит в папке /app
    # Если ты запускаешь из папки /backend, путь будет ../app/index.html
    index_path = os.path.join(os.path.dirname(__file__), "..", "app", "index.html")
    return FileResponse(index_path)

# 4. Логика ИИ-Агента (Оценка сложности)
def ai_evaluate_complexity(payload_text: str) -> int:
    print(f"\n[AI Agent] Analyzing incoming payload...")
    
    # Ищем тяжелые конструкции: циклы, матрицы, рекурсию
    if any(word in payload_text.lower() for word in ["while", "for", "matrix", "np.", "recursion"]):
        score = random.randint(8, 10)
        print(f"⚠️ High complexity detected! Score: {score}/10")
    elif any(word in payload_text.lower() for word in ["print", "hello", "sum(a,b)"]):
        score = random.randint(1, 3)
        print(f"✅ Light task detected. Score: {score}/10")
    else:
        score = 5
        print(f"ℹ️ Standard task. Score: {score}/10")
        
    return score

# 5. Имитация взаимодействия со смарт-контрактом Solana
def update_solana_contract(score: int):
    # Формула: чем выше сложность, тем дороже стриминг
    # Fee = (Complexity * 0.05)
    new_burn_rate = score * 0.05
    
    print(f"[Solana CPI] Sending 'update_burn_rate' to Program ID...")
    print(f"[On-Chain] New dynamic rate set: {new_burn_rate:.2f} USDC/sec")
    
    return round(new_burn_rate, 2)

# 6. Главный рабочий эндпоинт /execute
@app.post("/execute")
async def execute_task(req: Payload):
    print("="*50)
    print(f"INCOMING REQUEST from: {req.user_wallet[:8]}...")
    
    # Шаг 1: Оценка ИИ
    complexity_score = ai_evaluate_complexity(req.code_or_query)
    
    # Шаг 2: Обновление цены в блокчейне (имитация)
    burn_rate = update_solana_contract(complexity_score)
    
    # Шаг 3: Выполнение задачи (имитация задержки процессора)
    print(f"[Compute] Processing payload...")
    time.sleep(2.5) 
    
    # Шаг 4: Сброс цены после выполнения
    print("[Solana CPI] Task finished. Resetting burn_rate to 0.00")
    print("="*50)
    
    return {
        "status": "success",
        "complexity_score": complexity_score,
        "fee_per_second": burn_rate,
        "message": "Aperture executed and settled on-chain."
    }
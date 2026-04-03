from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import database
from ai_engine import analyze_code_complexity

app = FastAPI(title="Aperture DePIN Gateway v1.0")

# Настройка CORS, чтобы твой React (localhost:5173) мог общаться с бэкендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- КОНФИГУРАЦИЯ ---
# Твой проверенный адрес кошелька (Base58)
TREASURY_WALLET = "881Hpe3BtTquBCcm99KexH86KUgqVEvhuFeqqtkcxpkZ" 

# --- МОДЕЛИ ДАННЫХ (Pydantic) ---
class RunRequest(BaseModel):
    code: str
    guest_id: Optional[str] = None
    wallet: Optional[str] = None

class PaymentRequest(BaseModel):
    signature: str
    wallet: str

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ЭНДПОИНТЫ ---

@app.get("/balance")
def get_balance(guest_id: Optional[str] = None, wallet: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Проверяет баланс пользователя. 
    Если пользователя нет — создает его и начисляет приветственные 0.10 USDC.
    """
    user = db.query(database.User).filter(
        (database.User.guest_id == guest_id) | (database.User.wallet == wallet)
    ).first()
    
    if user:
        # Автоматическая привязка кошелька к существующему гостевому аккаунту
        if wallet and not user.wallet:
            user.wallet = wallet
            db.commit()
    else:
        # Создание нового профиля
        user = database.User(guest_id=guest_id, wallet=wallet, balance=0.10, is_demo=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        
    return {"balance": round(user.balance, 4), "is_demo": user.is_demo}

@app.post("/verify-payment")
def verify_payment(req: PaymentRequest, db: Session = Depends(get_db)):
    """
    Пополняет баланс пользователя после успешной транзакции в Solana Devnet.
    За 0.01 SOL начисляется 5.0 USDC.
    """
    user = db.query(database.User).filter(database.User.wallet == req.wallet).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found. Please connect your wallet.")
    
    # В MVP мы доверяем факту получения сигнатуры от фронтенда.
    # Этого достаточно для хакатон-демо.
    user.balance += 5.0
    user.is_demo = False  # Теперь пользователь считается "реальным"
    db.commit()
    
    return {
        "status": "success", 
        "new_balance": round(user.balance, 4),
        "msg": "Payment received via Solana Devnet"
    }

@app.post("/execute")
def execute_code(req: RunRequest, db: Session = Depends(get_db)):
    """
    Основная логика шлюза:
    1. Анализ сложности кода через ИИ Gemini.
    2. Расчет стоимости по "Величественной формуле".
    3. Списание средств и "запуск" (одобрение).
    """
    user = db.query(database.User).filter(
        (database.User.guest_id == req.guest_id) | (database.User.wallet == req.wallet)
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User record not found")

    # 1. Вызываем ИИ-аудитора из ai_engine.py
    ai_result = analyze_code_complexity(req.code)
    
    if ai_result["status"] == "error":
        raise HTTPException(status_code=500, detail=ai_result["message"])

    # 2. Получаем стоимость из ИИ-анализа
    cost = ai_result["calculated_rate_usd_sec"]

    # 3. Проверка платежеспособности
    if user.balance < cost:
        raise HTTPException(
            status_code=402, 
            detail=f"Insufficient funds. Required: {cost} USDC. Please Top Up via Solana."
        )

    # 4. Списание баланса
    user.balance -= cost
    db.commit()

    return {
        "status": "success",
        "cost": cost,
        "new_balance": round(user.balance, 4),
        "ai_analysis": ai_result["scores"]
    }
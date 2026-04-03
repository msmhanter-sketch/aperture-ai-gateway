from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import database
from ai_engine import analyze_code_complexity

app = FastAPI()

# Разрешаем фронтенду общаться с бэкендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ТВОЙ АДРЕС ДЛЯ ПРИЕМА ПЛАТЕЖЕЙ
TREASURY_WALLET = "ВАШ_SOL_АДРЕС" 

class RunRequest(BaseModel):
    code: str
    guest_id: Optional[str] = None
    wallet: Optional[str] = None

class PaymentRequest(BaseModel):
    signature: str
    wallet: str

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/balance")
def get_balance(guest_id: Optional[str] = None, wallet: Optional[str] = None, db: Session = Depends(get_db)):
    user = db.query(database.User).filter((database.User.guest_id == guest_id) | (database.User.wallet == wallet)).first()
    if user:
        if wallet and not user.wallet:
            user.wallet = wallet
            db.commit()
    else:
        user = database.User(guest_id=guest_id, wallet=wallet, balance=0.10, is_demo=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"balance": round(user.balance, 4), "is_demo": user.is_demo}

# НОВЫЙ ЭНДПОИНТ ДЛЯ ПОПОЛНЕНИЯ
@app.post("/verify-payment")
def verify_payment(req: PaymentRequest, db: Session = Depends(get_db)):
    user = db.query(database.User).filter(database.User.wallet == req.wallet).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Connect wallet first.")
    
    # В MVP мы верим фронтенду, что транзакция прошла (для хакатона это ок)
    # Начисляем 5.0 USDC за пополнение (0.01 SOL)
    user.balance += 5.0
    user.is_demo = False
    db.commit()
    return {"status": "success", "new_balance": round(user.balance, 4)}

@app.post("/execute")
def execute_code(req: RunRequest, db: Session = Depends(get_db)):
    user = db.query(database.User).filter((database.User.guest_id == req.guest_id) | (database.User.wallet == req.wallet)).first()
    
    ai_result = analyze_code_complexity(req.code)
    if ai_result["status"] == "error":
        raise HTTPException(status_code=500, detail=ai_result["message"])

    cost = ai_result["calculated_rate_usd_sec"]

    if user.balance < cost:
        raise HTTPException(status_code=402, detail="Low balance. Please Top Up.")

    user.balance -= cost
    db.commit()

    return {
        "status": "success",
        "cost": cost,
        "new_balance": round(user.balance, 4),
        "ai_analysis": ai_result["scores"]
    }
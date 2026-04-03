from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import database
from ai_engine import analyze_code_complexity

app = FastAPI(title="Aperture AI-Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Обновленная модель: теперь параметры могут быть пустыми (null)
class RunRequest(BaseModel):
    code: str
    guest_id: Optional[str] = None
    wallet: Optional[str] = None

@app.get("/balance")
def get_balance(guest_id: Optional[str] = None, wallet: Optional[str] = None, db: Session = Depends(get_db)):
    if not guest_id and not wallet:
        raise HTTPException(status_code=400, detail="Provide guest_id or wallet")
    
    # Ищем пользователя
    user = db.query(database.User).filter(
        (database.User.guest_id == guest_id) | (database.User.wallet == wallet)
    ).first()

    if user:
        # Если юзер зашел с кошельком, но в базе он еще гость — привязываем кошелек
        if wallet and not user.wallet:
            user.wallet = wallet
            db.commit()
            db.refresh(user)
    else:
        # Создаем нового гостя
        user = database.User(guest_id=guest_id, wallet=wallet, balance=0.10, is_demo=True)
        db.add(user)
        db.commit()
        db.refresh(user)

    return {"balance": round(user.balance, 4), "is_demo": user.is_demo}

@app.post("/execute")
def execute_code(req: RunRequest, db: Session = Depends(get_db)):
    user = db.query(database.User).filter(
        (database.User.guest_id == req.guest_id) | (database.User.wallet == req.wallet)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found in Gateway. Re-sync wallet.")

    ai_result = analyze_code_complexity(req.code)
    if ai_result["status"] == "error":
        raise HTTPException(status_code=500, detail=ai_result["message"])

    cost = ai_result["calculated_rate_usd_sec"]

    if user.balance < cost:
        raise HTTPException(status_code=402, detail="Trial period exhausted. Connect Solana Wallet.")

    user.balance -= cost
    db.commit()

    return {
        "status": "success",
        "cost": cost,
        "new_balance": round(user.balance, 4),
        "ai_analysis": ai_result["scores"]
    }
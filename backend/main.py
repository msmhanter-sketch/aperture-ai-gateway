import uuid
import database
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict, List
from contextlib import asynccontextmanager

# 🔥 ИМПОРТЫ ТВОИХ МОДУЛЕЙ
from ai_engine import analyze_code_complexity
from solana_client import SolanaClient

# ==========================================
# 🧠 LIFESPAN (Управление ресурсами)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Действия при старте
    print("🟢 Aperture Protocol: Neural Links Established.")
    yield
    # Действия при выключении
    await solana_client.close()
    print("🛑 Aperture Protocol: Systems Offline.")

app = FastAPI(title="Aperture DePIN Gateway v1.1", lifespan=lifespan)
solana_client = SolanaClient()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TREASURY_WALLET = "881Hpe3BtTquBCcm99KexH86KUgqVEvhuFeqqtkcxpkZ" 

# ==========================================
# 🧱 МОДЕЛИ
# ==========================================
class RunRequest(BaseModel):
    code: str
    guest_id: Optional[str] = None
    wallet: Optional[str] = None

class PaymentRequest(BaseModel):
    signature: str
    wallet: str

class NodeInfo(BaseModel):
    node_id: str
    gpu_name: str
    vram_total: float
    status: str

# Хранилища в памяти (для быстрой работы очереди)
nodes: Dict[str, dict] = {}
pending_tasks: List[dict] = []
completed_tasks: Dict[str, str] = {}

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 📡 СИСТЕМНЫЕ ЭНДПОИНТЫ
# ==========================================
@app.get("/health")
async def health():
    return {"status": "online", "nodes_active": len(nodes)}

# ==========================================
# 🦾 DePIN ИНФРАСТРУКТУРА (Nodes & Tasks)
# ==========================================
@app.post("/register_node")
async def register_node(info: NodeInfo):
    # Используем model_dump() вместо dict() для Pydantic V2
    nodes[info.node_id] = info.model_dump()
    return {"status": "registered", "node_id": info.node_id}

@app.get("/active_nodes")
async def get_nodes():
    return list(nodes.values())

@app.get("/get_task")
def get_task():
    if pending_tasks:
        task = pending_tasks.pop(0)
        print(f"[📡] Task {task['task_id']} dispatched to node.")
        return task
    return {"task_id": None}

@app.post("/submit_result")
def submit_result(payload: dict):
    task_id = payload.get("task_id")
    output = payload.get("output")
    completed_tasks[task_id] = output
    print(f"[🚀] RESULT RECEIVED: {task_id}")
    return {"status": "saved"}

@app.get("/result/{task_id}")
def get_task_result(task_id: str):
    if task_id in completed_tasks:
        return {
            "status": "completed",
            "task_id": task_id,
            "output": completed_tasks[task_id]
        }
    
    for task in pending_tasks:
        if task["task_id"] == task_id:
            return {"status": "processing"}
            
    raise HTTPException(status_code=404, detail="Task not found in logs")

# ==========================================
# 💰 ЯДРО ИСПОЛНЕНИЯ И ФИНАНСОВ
# ==========================================
@app.get("/balance")
def get_balance(guest_id: Optional[str] = None, wallet: Optional[str] = None, db: Session = Depends(get_db)):
    user = db.query(database.User).filter(
        (database.User.guest_id == guest_id) | (database.User.wallet == wallet)
    ).first()
    
    if not user:
        user = database.User(guest_id=guest_id, wallet=wallet, balance=0.10, is_demo=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        
    return {"balance": round(user.balance, 4), "is_demo": user.is_demo}

@app.post("/execute")
async def execute_code(req: RunRequest, db: Session = Depends(get_db)):
    # Находим или создаем юзера (чтобы не было 404)
    user = db.query(database.User).filter(
        (database.User.guest_id == req.guest_id) | (database.User.wallet == req.wallet)
    ).first()
    
    if not user:
        user = database.User(guest_id=req.guest_id, wallet=req.wallet, balance=0.10, is_demo=True)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 1. Анализ кода
    ai_result = analyze_code_complexity(req.code)
    if ai_result["status"] == "error":
        raise HTTPException(status_code=400, detail=ai_result["message"])

    cost = ai_result["calculated_rate_usd_sec"]
    
    # 2. Проверка баланса
    if user.balance < cost:
        raise HTTPException(status_code=402, detail=f"Insufficient funds. Need {cost} USDC")

    # 3. Блокчейн-логика (Solana)
    burn_rate_lamports = int(cost * 1_000_000_000)
    target_wallet = req.wallet if req.wallet else "11111111111111111111111111111111"
    tx_success = await solana_client.update_burn_rate(target_wallet, burn_rate_lamports)

    # 4. Списание и постановка в очередь
    user.balance -= cost
    db.commit()

    task_id = f"task-{uuid.uuid4().hex[:6]}"
    pending_tasks.append({
        "task_id": task_id,
        "code": req.code
    })

    print(f"[*] Task {task_id} queued. Cost: {cost}")

    return {
        "status": "success",
        "task_id": task_id,
        "cost": cost,
        "new_balance": round(user.balance, 4),
        "ai_analysis": ai_result["scores"],
        "tx_status": "success" if tx_success else "failed" 
    }

if __name__ == "__main__":
    import uvicorn
    # Запускаем на 0.0.0.0 чтобы было видно из всех сетей
    uvicorn.run(app, host="0.0.0.0", port=8000)
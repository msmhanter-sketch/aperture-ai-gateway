import uuid
import time
import database
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict, List
from contextlib import asynccontextmanager

# 🔥 ИМПОРТЫ КВАНТОВОГО ДВИЖКА (Убедись, что ai_engine.py обновлен)
from ai_engine import analyze_code_complexity, calculate_quantum_price
from solana_client import SolanaClient

# ==========================================
# 🧠 LIFESPAN & INITIALIZATION
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🟢 Aperture Protocol: Neural Links Established.")
    yield
    await solana_client.close()
    print("🛑 Aperture Protocol: Systems Offline.")

app = FastAPI(title="Aperture DePIN Gateway v1.3", lifespan=lifespan)
solana_client = SolanaClient()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- IN-MEMORY СТЕЙТ (ОЧЕРЕДЬ И ТЕЛЕМЕТРИЯ) ---
nodes: Dict[str, dict] = {}
pending_tasks: List[dict] = []
completed_tasks: Dict[str, str] = {}
active_tasks_rates = {}  # Хранилище для активного биллинга и APS

# ==========================================
# 🧱 MODELS
# ==========================================
class RunRequest(BaseModel):
    code: str
    wallet: str
    guest_id: Optional[str] = "guest"

class NodeInfo(BaseModel):
    node_id: str
    gpu_name: str
    vram_total: float

def get_db():
    db = database.SessionLocal()
    try: yield db
    finally: db.close()

# ==========================================
# 💰 ФИНАНСОВОЕ ЯДРО (BILLING)
# ==========================================

@app.get("/balance/{wallet_address}")
def get_balance(wallet_address: str, db: Session = Depends(get_db)):
    """Синхронизация баланса для защиты от халявы при F5"""
    user = db.query(database.User).filter(database.User.wallet == wallet_address).first()
    if not user:
        user = database.User(guest_id="guest", wallet=wallet_address, balance=0.01, is_demo=True)
        db.add(user)
        db.commit()
    return {"balance": round(user.balance, 6)}

@app.post("/execute")
async def execute_code(req: RunRequest, db: Session = Depends(get_db)):
    """Инициирует выполнение и запускает стриминговый биллинг"""
    user = db.query(database.User).filter(database.User.wallet == req.wallet).first()
    if not user:
        user = database.User(guest_id=req.guest_id, wallet=req.wallet, balance=0.01, is_demo=True)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 1. Квантовый аудит (ИИ-прогноз)
    ai_result = analyze_code_complexity(req.code)
    burn_rate = ai_result.get("calculated_rate_usd_sec", 0.0005)
    comp_sum = ai_result.get("complexity_sum", 10)

    # 2. Проверка 'Gas Limit' (минимум на 3 секунды работы)
    if user.balance < (burn_rate * 3):
        raise HTTPException(
            status_code=402, 
            detail=f"Insufficient funds. Required: {(burn_rate * 3):.6f} CRD."
        )

    task_id = f"task-{uuid.uuid4().hex[:6]}"
    
    # 3. Регистрация в биллинговой системе
    active_tasks_rates[task_id] = {
        "wallet": req.wallet,
        "rate": burn_rate,
        "comp_sum": comp_sum,
        "start_time": time.time()
    }

    pending_tasks.append({"task_id": task_id, "code": req.code})
    print(f"[*] Task {task_id} launched. Expected Rate: {burn_rate}/sec")

    return {
        "status": "success",
        "task_id": task_id,
        "burn_rate": burn_rate,
        "current_balance": user.balance,
        "ai_analysis": ai_result.get("scores", {})
    }

@app.post("/stop/{task_id}")
async def stop_task(task_id: str, db: Session = Depends(get_db)):
    """Экстренная остановка задачи пользователем"""
    if task_id in active_tasks_rates:
        info = active_tasks_rates.pop(task_id)
        duration = time.time() - info["start_time"]
        
        # Считаем стоимость без APS штрафа (т.к. остановлено вручную)
        final_cost = duration * info["rate"]

        user = db.query(database.User).filter(database.User.wallet == info["wallet"]).first()
        if user:
            user.balance -= final_cost
            db.commit()
            print(f"[🛑] ABORTED: Task {task_id}. Execution duration: {duration:.2f}s.")

        completed_tasks[task_id] = "EXECUTION_ABORTED_BY_USER"
        return {"status": "stopped", "final_cost": final_cost}
    
    raise HTTPException(status_code=404, detail="Task not found or already completed")

@app.post("/submit_result")
def submit_result(payload: dict, db: Session = Depends(get_db)):
    """Финальный расчет (Settlement) при завершении нодой"""
    task_id = payload.get("task_id")
    output = payload.get("output")
    
    if task_id in active_tasks_rates:
        info = active_tasks_rates.pop(task_id)
        duration = time.time() - info["start_time"]
        
        # 🔥 ПРИМЕНЕНИЕ APS (Aperture Penalty Scale) 🔥
        # Имитация дельты: если код крутился дольше 2с, считаем что нагрузка превысила лимиты
        telemetry_delta = 0.6 if duration > 2.0 else 0.0
        
        final_rate = calculate_quantum_price(
            complexity_sum=info["comp_sum"], 
            hw_power=1.2, 
            telemetry_delta=telemetry_delta
        )
        
        final_cost = duration * final_rate

        user = db.query(database.User).filter(database.User.wallet == info["wallet"]).first()
        if user:
            user.balance -= final_cost
            db.commit()
            print(f"[💰] SETTLEMENT: {task_id}. Duration: {duration:.2f}s.")
            print(f"    Rate adjustment: {info['rate']:.6f} -> {final_rate:.6f} (APS: {'ON' if telemetry_delta > 0 else 'OFF'})")

    completed_tasks[task_id] = output
    return {"status": "saved"}

# ==========================================
# 🛰️ INFRASTRUCTURE & MONITORING
# ==========================================

@app.get("/result/{task_id}")
def get_result(task_id: str):
    if task_id in completed_tasks:
        return {"status": "completed", "output": completed_tasks[task_id]}
    return {"status": "processing"}

@app.post("/register_node")
async def register_node(info: NodeInfo):
    nodes[info.node_id] = {
        "gpu_name": info.gpu_name, 
        "node_id": info.node_id, 
        "vram_total": info.vram_total, 
        "last_seen": time.time()
    }
    return {"status": "registered"}

@app.get("/active_nodes")
async def get_nodes():
    now = time.time()
    return [n for n in nodes.values() if now - n["last_seen"] < 30]

@app.get("/get_task")
def get_task():
    if pending_tasks:
        task = pending_tasks.pop(0)
        print(f"[📡] Task {task['task_id']} dispatched to provider node.")
        return task
    return {"task_id": None}

if __name__ == "__main__":
    import uvicorn
    # Запуск на 0.0.0.0 для доступа извне
    uvicorn.run(app, host="0.0.0.0", port=8000)
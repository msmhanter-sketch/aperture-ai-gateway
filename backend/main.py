import uuid
import time
import asyncio
import database
import base58
import requests
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse # Для отдачи логов файлом
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict, List
from contextlib import asynccontextmanager
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

# Твои модули
from ai_engine import analyze_code_complexity
from solana_client import SolanaClient

HELIUS_API_KEY = "04eaffb2-c41c-4bd4-967d-a64f7b1bab1a"
HELIUS_URL = f"https://devnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# --- УТИЛИТЫ ---

def verify_signature(public_key_str: str, signature_bytes: list, message_str: str):
    try:
        public_key_bytes = base58.b58decode(public_key_str)
        verify_key = VerifyKey(public_key_bytes)
        sig_bytes = bytes(signature_bytes)
        msg_bytes = message_str.encode("utf-8")
        verify_key.verify(msg_bytes, sig_bytes)
        return True
    except (BadSignatureError, Exception) as e:
        print(f"[!] Web3 Auth Failed: {e}")
        return False

def mint_compute_receipt(wallet: str, task_id: str, duration: float, cost: float, ai_verdict: str):
    """Минтинг cNFT чека через Helius"""
    print(f"[🛠️] Minting receipt for {wallet}...")
    payload = {
        "jsonrpc": "2.0",
        "id": "aperture-mint",
        "method": "mintCompressedNft",
        "params": {
            "name": f"Aperture Task {task_id[-4:]}",
            "symbol": "APRT",
            "owner": wallet,
            "description": f"AI Compute Receipt. Verdict: {ai_verdict}",
            "attributes": [
                {"trait_type": "Duration", "value": f"{duration:.2f}s"},
                {"trait_type": "Cost", "value": f"{cost:.8f} SOL"},
                {"trait_type": "Task_ID", "value": task_id}
            ],
            "imageUrl": "https://raw.githubusercontent.com/solana-foundation/press-kit/main/Solana_Logo_Symbol_Gradient.png",
            "externalUrl": "https://aperture-ai.vercel.app"
        }
    }
    try:
        response = requests.post(HELIUS_URL, json=payload, timeout=10)
        res_data = response.json()
        if "result" in res_data:
            print(f"[⛓️] ON-CHAIN RECEIPT MINTED: {res_data['result']['signature']}")
            return res_data['result']['signature']
        else:
            print(f"[!] Minting Failed: {res_data.get('error')}")
    except Exception as e:
        print(f"[!] Helius Request Error: {e}")
    return None

# --- APP CONFIG ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🟢 Aperture AI Oracle: Systems Online. Helius Connected.")
    yield
    await solana_client.close()
    print("🛑 Aperture AI Oracle: Systems Offline.")

app = FastAPI(title="Aperture Autonomous AI Gateway", lifespan=lifespan)
solana_client = SolanaClient() 

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Память сервера
nodes: Dict[str, dict] = {}
pending_tasks: List[dict] = []
completed_tasks: Dict[str, str] = {}
active_tasks_rates = {} 

class RunRequest(BaseModel):
    code: str
    wallet: str
    signature: List[int]
    message: str          
    guest_id: Optional[str] = "guest"

class DepositRequest(BaseModel):
    wallet: str
    signature: str 
    amount: float

class NodeInfo(BaseModel):
    node_id: str
    gpu_name: str
    vram_total: float

def get_db():
    db = database.SessionLocal()
    try: yield db
    finally: db.close()

# --- ROUTES ---

@app.get("/price")
def get_sol_price():
    """Эндпоинт для получения цены SOL (фикс 404)"""
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT", timeout=2)
        price = float(r.json()['price'])
        return {"price": price}
    except Exception:
        return {"price": 182.45}

@app.get("/balance/{wallet_address}")
def get_balance(wallet_address: str, db: Session = Depends(get_db)):
    user = db.query(database.User).filter(database.User.wallet == wallet_address).first()
    if not user:
        user = database.User(guest_id="guest", wallet=wallet_address, balance=0.0, is_demo=False)
        db.add(user)
        db.commit()
    return {"balance": round(user.balance, 8)}

@app.post("/deposit")
async def process_deposit(req: DepositRequest, db: Session = Depends(get_db)):
    user = db.query(database.User).filter(database.User.wallet == req.wallet).first()
    if not user:
        user = database.User(guest_id="guest", wallet=req.wallet, balance=0.0, is_demo=False)
        db.add(user)
    
    user.balance += req.amount
    db.commit()
    return {"status": "success", "new_balance": user.balance}

@app.post("/execute")
async def execute_code(req: RunRequest, db: Session = Depends(get_db)):
    if not verify_signature(req.wallet, req.signature, req.message):
        raise HTTPException(status_code=401, detail="Invalid Signature")

    user = db.query(database.User).filter(database.User.wallet == req.wallet).first()
    
    if not user or user.balance < 0.001:
        raise HTTPException(status_code=402, detail="Insufficient SOL for startup fee (0.001 required)")

    # Входной билет
    STARTUP_FEE = 0.001
    user.balance = max(0, user.balance - STARTUP_FEE)
    db.commit()
    print(f"[🎟️] STARTUP FEE COLLECTED: {req.wallet} paid {STARTUP_FEE} SOL.")

    ai_result = analyze_code_complexity(req.code)
    
    if ai_result.get("security") == "DANGEROUS":
        print(f"[🚨] MALICIOUS CODE BLOCKED from {req.wallet}")
        raise HTTPException(status_code=403, detail="AI Sentinel blocked execution: Malicious code detected.")

    burn_rate = ai_result.get("calculated_rate_sol_sec", 0.0001)
    ai_verdict = ai_result.get("scores", {}).get("reason", "AI Verified Compute")
    
    task_id = f"task-{uuid.uuid4().hex[:6]}"

    # Отправляем AI-вердикт в ончейн (Solana)
    try:
        tx_sig = await solana_client.send_ai_verdict(user_wallet=req.wallet, task_id=task_id, burn_rate=burn_rate)
        on_chain_proof = f"https://explorer.solana.com/tx/{tx_sig}?cluster=devnet"
    except Exception:
        on_chain_proof = "Pending confirmation..."

    active_tasks_rates[task_id] = {
        "wallet": req.wallet,
        "rate": burn_rate,
        "start_time": time.time(),
        "proof": on_chain_proof,
        "ai_verdict": ai_verdict
    }

    pending_tasks.append({"task_id": task_id, "code": req.code})
    
    return {
        "status": "success",
        "task_id": task_id,
        "burn_rate": burn_rate,
        "startup_fee_paid": STARTUP_FEE,
        "current_balance": user.balance,
        "on_chain_proof": on_chain_proof
    }

@app.post("/submit_result")
def submit_result(payload: dict, db: Session = Depends(get_db)):
    task_id = payload.get("task_id")
    output = payload.get("output")
    execution_time = payload.get("execution_time", 0) 
    
    if task_id in active_tasks_rates:
        info = active_tasks_rates.pop(task_id)
        # Считаем итоговую стоимость выполнения
        final_cost = round(execution_time * info["rate"], 8)

        user = db.query(database.User).filter(database.User.wallet == info["wallet"]).first()
        if user:
            user.balance = max(0, user.balance - final_cost)
            db.commit()
            
            # Общая стоимость для чека (фи плюс выполнение)
            total_cost_for_receipt = final_cost + 0.001 
            
            # Выпуск NFT чека
            mint_compute_receipt(
                wallet=info["wallet"],
                task_id=task_id,
                duration=execution_time,
                cost=total_cost_for_receipt,
                ai_verdict=info["ai_verdict"]
            )
            print(f"[💰] SETTLEMENT: {task_id}. Execution charged: {final_cost:.8f} SOL.")

    # Сохраняем ПОЛНЫЙ аутпут для возможности скачивания
    completed_tasks[task_id] = output
    return {"status": "saved"}

@app.post("/stop/{task_id}")
async def stop_task(task_id: str, db: Session = Depends(get_db)):
    if task_id in active_tasks_rates:
        info = active_tasks_rates.pop(task_id)
        duration = time.time() - info["start_time"]
        final_cost = round(duration * info["rate"], 8)
        
        user = db.query(database.User).filter(database.User.wallet == info["wallet"]).first()
        if user:
            user.balance = max(0, user.balance - final_cost)
            db.commit()
            print(f"[🛑] TASK ABORTED: {task_id}. Charged: {final_cost:.8f} SOL.")
        
        completed_tasks[task_id] = "EXECUTION_ABORTED_BY_USER"
        return {"status": "stopped", "final_cost": final_cost}
    raise HTTPException(status_code=404, detail="Task not found")

@app.get("/result/{task_id}")
def get_result(task_id: str):
    if task_id in completed_tasks:
        return {"status": "completed", "output": completed_tasks[task_id]}
    return {"status": "processing"}

@app.get("/download/{task_id}")
def download_result(task_id: str):
    """Возвращает полный лог задачи в виде .txt файла для скачивания"""
    if task_id in completed_tasks:
        content = completed_tasks[task_id]
        return PlainTextResponse(
            content, 
            headers={"Content-Disposition": f"attachment; filename=aperture_log_{task_id}.txt"}
        )
    raise HTTPException(status_code=404, detail="Log file not found or task incomplete")

@app.post("/register_node")
async def register_node(info: NodeInfo):
    nodes[info.node_id] = {"gpu_name": info.gpu_name, "last_seen": time.time()}
    return {"status": "registered"}

@app.get("/active_nodes")
async def get_nodes():
    now = time.time()
    return [n for n in nodes.values() if now - n["last_seen"] < 30]

@app.get("/get_task")
def get_task():
    if pending_tasks:
        return pending_tasks.pop(0)
    return {"task_id": None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
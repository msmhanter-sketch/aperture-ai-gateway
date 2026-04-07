import os
import uuid
import time
import asyncio
import base58
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, Dict, List
from contextlib import asynccontextmanager
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from ai_engine import analyze_code_complexity
from solana_client import SolanaClient

load_dotenv()

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "04eaffb2-c41c-4bd4-967d-a64f7b1bab1a")
HELIUS_URL = f"https://devnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

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
    except Exception as e:
        print(f"[!] Helius Request Error: {e}")
    return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🟢 Aperture AI Oracle: Systems Online.")
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

# --- ПАМЯТЬ СЕРВЕРА (Только временные логи и воркеры) ---
nodes: Dict[str, dict] = {}
pending_tasks: List[dict] = []
completed_tasks: Dict[str, str] = {} 
full_logs: Dict[str, str] = {}       
active_tasks_rates = {} 

class RunRequest(BaseModel):
    code: str
    wallet: str
    signature: List[int]
    message: str          
    guest_id: Optional[str] = "guest"

class NodeInfo(BaseModel):
    node_id: str
    gpu_name: str
    vram_total: float

@app.get("/price")
def get_sol_price():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT", timeout=2)
        return {"price": float(r.json()['price'])}
    except Exception:
        return {"price": 182.45}

@app.get("/balance/{wallet_address}")
async def get_balance(wallet_address: str):
    """Теперь мы читаем баланс прямо из смарт-контракта!"""
    try:
        # Эта функция появится в solana_client на следующем шаге
        balance_lamports = await solana_client.get_channel_balance(wallet_address)
        balance_sol = balance_lamports / 1_000_000_000
        return {"balance": round(balance_sol, 8)}
    except Exception as e:
        print(f"🔴 Error reading on-chain balance: {e}")
        return {"balance": 0.0}

@app.post("/execute")
async def execute_code(req: RunRequest):
    if not verify_signature(req.wallet, req.signature, req.message):
        raise HTTPException(status_code=401, detail="Invalid Signature")

    # Проверяем баланс On-Chain
    balance_lamports = await solana_client.get_channel_balance(req.wallet)
    if balance_lamports < 1000000: # Минимум 0.001 SOL (в лампортах)
        raise HTTPException(status_code=402, detail="Insufficient locked SOL in Payment Channel.")

    # 🧠 ВЫЗОВ ИИ-ОРАКУЛА
    ai_result = analyze_code_complexity(req.code)
    
    reason = ai_result.get("scores", {}).get("reason", "No explanation provided.")
    complexity = ai_result.get("complexity_score", 0)
    burn_rate_sol = ai_result.get("calculated_rate_sol_sec", 0.00000100)
    
    # Переводим SOL в Lamports (1 SOL = 10^9 Lamports)
    burn_rate_lamports = int(burn_rate_sol * 1_000_000_000)

    print("\n" + "="*50)
    print(f"🧠 [AGENT REASONING]: {reason}")
    print(f"📊 [COMPLEXITY SCORE]: {complexity}/100")
    print(f"🔥 [DYNAMIC RATE]: {burn_rate_sol:.8f} SOL/sec ({burn_rate_lamports} lamports)")
    print("="*50 + "\n")

    if ai_result.get("security") == "DANGEROUS":
        print(f"[🚨] MALICIOUS CODE BLOCKED from {req.wallet}")
        raise HTTPException(status_code=403, detail="AI Sentinel blocked execution: Malicious code detected.")

    ai_verdict = ai_result.get("scores", {}).get("reason", "AI Verified Compute")
    task_id = f"task-{uuid.uuid4().hex[:6]}"

    # 🔗 МАГИЯ: ИИ МЕНЯЕТ СТЕЙТ БЛОКЧЕЙНА (ВКЛЮЧАЕТ СЧЕТЧИК)
    tx_sig = await solana_client.update_burn_rate(user_pubkey_str=req.wallet, new_rate_lamports=burn_rate_lamports)
    
    if not tx_sig:
        raise HTTPException(status_code=500, detail="Failed to update smart contract state. Execution aborted.")

    on_chain_proof = f"https://explorer.solana.com/tx/{tx_sig}?cluster=devnet"

    active_tasks_rates[task_id] = {
        "wallet": req.wallet,
        "rate_sol": burn_rate_sol,
        "start_time": time.time(),
        "proof": on_chain_proof,
        "ai_verdict": ai_verdict
    }

    pending_tasks.append({"task_id": task_id, "code": req.code, "wallet": req.wallet})
    
    return {
        "status": "success",
        "task_id": task_id,
        "burn_rate": burn_rate_sol,
        "on_chain_proof": on_chain_proof
    }

@app.post("/submit_result")
async def submit_result(payload: dict):
    task_id = payload.get("task_id")
    output = payload.get("output", "")
    full_log_data = payload.get("full_log", output) 
    execution_time = payload.get("execution_time", 0) 
    
    if task_id in active_tasks_rates:
        info = active_tasks_rates.pop(task_id)
        final_cost = round(execution_time * info["rate_sol"], 8)

        # 🔗 МАГИЯ: ИИ ОСТАНАВЛИВАЕТ СЧЕТЧИК В БЛОКЧЕЙНЕ (rate = 0)
        stop_sig = await solana_client.update_burn_rate(user_pubkey_str=info["wallet"], new_rate_lamports=0)
        print(f"🛑 [ON-CHAIN] Burn rate set to 0. Stop TX: {stop_sig}")
        
        # Минтим чек
        mint_compute_receipt(
            wallet=info["wallet"],
            task_id=task_id,
            duration=execution_time,
            cost=final_cost,
            ai_verdict=info["ai_verdict"]
        )

    completed_tasks[task_id] = output          
    full_logs[task_id] = full_log_data         
    return {"status": "saved"}

@app.post("/stop/{task_id}")
async def stop_task(task_id: str):
    if task_id in active_tasks_rates:
        info = active_tasks_rates.pop(task_id)
        
        # 🔗 ОСТАНАВЛИВАЕМ СЧЕТЧИК В БЛОКЧЕЙНЕ ПРИ ПРИНУДИТЕЛЬНОЙ ОТМЕНЕ
        stop_sig = await solana_client.update_burn_rate(user_pubkey_str=info["wallet"], new_rate_lamports=0)
        print(f"🛑 [ON-CHAIN] User aborted task. Burn rate set to 0. Stop TX: {stop_sig}")
        
        completed_tasks[task_id] = "EXECUTION_ABORTED_BY_USER"
        return {"status": "stopped"}
    raise HTTPException(status_code=404, detail="Task not found")

@app.get("/result/{task_id}")
def get_result(task_id: str):
    if task_id in completed_tasks:
        return {"status": "completed", "output": completed_tasks[task_id]}
    return {"status": "processing"}

@app.get("/download/{task_id}")
def download_result(task_id: str):
    if task_id in full_logs:
        content = full_logs[task_id]
        return PlainTextResponse(
            content, 
            headers={"Content-Disposition": f"attachment; filename=aperture_log_{task_id}.txt"}
        )
    raise HTTPException(status_code=404, detail="Log file not found")

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
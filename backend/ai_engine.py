import math
import json
import os
import requests
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

def get_sol_price_from_pyth():
    """🔗 БРОНЕБОЙНЫЙ ОРАКУЛ (Pyth -> Binance -> Hardcode)"""
    try:
        price_id = "ef0d8b6fda2ceba41da15d4095d1da99f0e283034f2ff974b299a34f758f361b"
        url = f"https://hermes.pyth.network/v2/updates/price/latest?ids%5B%5D={price_id}"
        
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            price_info = data['parsed'][0]['price']
            raw_price = float(price_info['price'])
            exponent = float(price_info['expo'])
            return round(raw_price * (10 ** exponent), 2)
        else:
            raise Exception(f"Pyth API HTTP {response.status_code}")
            
    except Exception as e:
        print(f"[!] Pyth Oracle Blocked: {e}. Switching to Binance...")
        try:
            res = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT", timeout=3)
            return round(float(res.json()['price']), 2)
        except Exception as e2:
            print(f"[!] Binance API Error: {e2}. Using hard fallback.")
            return 182.00 # Актуальный курс на 2026

def sigmoid(x):
    """Сигмоида для Aperture Penalty Scale (APS)"""
    try:
        return 1 / (1 + math.exp(-15 * (x - 0.4)))
    except OverflowError:
        return 0 if x < 0.4 else 1

def calculate_quantum_price(complexity_sum, hw_power=2.5, telemetry_delta=0.0):
    """
    💎 ПОСЕКУНДНЫЙ ТАРИФ (ROBIN HOOD MODE)
    Цель: ~$1.30/час для стандартных задач.
    """
    # Снизили базу в 100 раз (было 0.00015)
    # 0.0000015 SOL/sec * 3600 sec * $180 ≈ $0.97/hour (Base)
    base_rate_sol = 0.0000015 
    
    if complexity_sum <= 0:
        return 0.00000050 # Абсолютный минимум (ECO)
        
    # Масштабируем сложность
    complexity_factor = (complexity_sum / 30) 
    
    # Итоговый рейт в секунду
    rate_per_sec = (base_rate_sol * complexity_factor) / hw_power
    
    # Множитель APS (на случай перегрузки ноды)
    aps_multiplier = 1 + (2 * sigmoid(telemetry_delta))
    
    final_rate = round(rate_per_sec * aps_multiplier, 8)
    
    # Ограничиваем "вилку" цен: от $0.30 до $5.00 за час в эквиваленте SOL
    return max(final_rate, 0.00000100)

def analyze_code_complexity(code_snippet: str):
    """
    🛡️ AI SENTINEL AUDIT (Security + Prediction + Fair Pricing)
    """
    prompt = f"""
    You are the strict AI Sentinel protecting a DePIN compute node.
    Your job is to enforce strict Sandbox isolation. Guest code must be PURELY computational.

    Analyze this Python code:
    1. SECURITY: If the code uses 'subprocess', 'os.system', 'socket', or 'requests' to hit local network, set "security": "DANGEROUS".
    2. COMPLEXITY: Estimate CPU/RAM usage (1-100).
    3. PREDICTION: How many seconds will this take to run?

    Respond ONLY in strict JSON format:
    {{
      "security": "SAFE" | "DANGEROUS",
      "predicted_sec": 5,
      "cpu": 10,
      "ram": 5,
      "network": 0,
      "reason": "Clear explanation"
    }}
    
    Code:
    {code_snippet}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', # Используем актуальную модель
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1 
            ),
        )
        
        result = json.loads(response.text)
        
        # Вытаскиваем баллы сложности
        cpu_score = result.get("cpu", 10)
        ram_score = result.get("ram", 10)
        net_score = result.get("network", 0)
        
        total_complexity = cpu_score + ram_score + net_score
        security_status = result.get("security", "SAFE").upper()
        
        # ПРОВЕРКА НА БЕСКОНЕЧНЫЕ ЦИКЛЫ (Дополнительный множитель сложности)
        if "while True" in code_snippet or "range(10**9)" in code_snippet:
            total_complexity *= 3.0
            if security_status == "SAFE":
                security_status = "WARNING"
            result["reason"] += " [SYSTEM: Extreme loop detected - High cost applied]"

        # РАСЧЕТ ЧЕСТНОЙ ЦЕНЫ
        price_per_sec = calculate_quantum_price(total_complexity, 2.5, 0.0)
        
        return {
            "status": "success",
            "security": security_status,
            "predicted_sec": result.get("predicted_sec", 5),
            "scores": result,
            "complexity_sum": total_complexity,
            "calculated_rate_sol_sec": price_per_sec, # Тот самый "Robin Hood" рейт
            "sol_market_price": get_sol_price_from_pyth()
        }
        
    except Exception as e:
        print(f"[!] AI Engine Error: {e}")
        # Если AI упал, шлем безопасный минимальный рейт
        return {
            "status": "error",
            "security": "SAFE",
            "predicted_sec": 5,
            "scores": {"cpu": 10, "ram": 5, "network": 0, "reason": "Audit bypass, using safety rate"},
            "calculated_rate_sol_sec": 0.00000080,
            "sol_market_price": get_sol_price_from_pyth()
        }
import math
import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Загружаем ключи
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Инициализация клиента
client = genai.Client(api_key=GEMINI_API_KEY)

def sigmoid(x):
    """
    Сигмоида для Aperture Penalty Scale (APS) - 'Налог на хитрожопость'.
    Возвращает значение от 0 до 1. Резко растет, если отклонение нагрузки > 0.4.
    """
    try:
        return 1 / (1 + math.exp(-15 * (x - 0.4)))
    except OverflowError:
        return 0 if x < 0.4 else 1

def calculate_quantum_price(complexity_sum, hw_power=1.2, telemetry_delta=0.0):
    """
    Aperture Quantum Pricing: Rate = (P_base * ln(1 + sum_C) * (1 + 10 * sigmoid(delta))) / H_perf
    """
    base_rate = 0.0005  # Базовая цена в CRD
    
    if complexity_sum <= 0:
        return base_rate
        
    # 1. Базовая часть (Сглаженный логарифмический рост)
    # math.log1p(x) - это безопасный ln(1 + x)
    base_part = base_rate * math.log1p(complexity_sum)
    
    # 2. APS (Динамический штраф по факту выполнения)
    aps_multiplier = 1 + (10 * sigmoid(telemetry_delta))
    
    # 3. Финальная цена с учетом железа (H_perf)
    rate = (base_part * aps_multiplier) / hw_power
    
    return round(rate, 6)

def analyze_code_complexity(code_snippet: str):
    prompt = f"""
    You are an expert AI code auditor for a DePIN compute network.
    Analyze the following Python code and estimate its resource complexity (1-100) for:
    - CPU: Loops, math, recursion.
    - RAM: Arrays, heavy imports.
    - Network: API calls, data transfer.
    
    Respond ONLY in strict JSON format:
    {{"cpu": 10, "ram": 5, "network": 0, "reason": "Explanation"}}
    
    Code:
    {code_snippet}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1 
            ),
        )
        
        result = json.loads(response.text)
        
        cpu_score = result.get("cpu", 1)
        ram_score = result.get("ram", 1)
        net_score = result.get("network", 0)
        
        total_complexity = cpu_score + ram_score + net_score
        
        # 🔥 СТАТИЧЕСКИЙ АНТИ-ЧИТ (Предварительный штраф) 🔥
        # Если ИИ видит откровенную дичь еще до запуска, завышаем сложность авансом
        if "math.factorial" in code_snippet or "secrets" in code_snippet or "while True" in code_snippet:
            total_complexity *= 3 
            result["reason"] += " [SYSTEM WARNING: Heavy load patterns detected. Complexity multiplied.]"
        
        # Считаем стартовую цену (telemetry_delta = 0, так как код еще не запускался)
        price_per_sec = calculate_quantum_price(
            complexity_sum=total_complexity,
            hw_power=1.2, # Задаем индекс для Google VM
            telemetry_delta=0.0
        )
        
        return {
            "status": "success",
            "scores": result,
            "complexity_sum": total_complexity, # Возвращаем сумму, чтобы main.py мог сверить ее с фактом
            "calculated_rate_usd_sec": price_per_sec
        }
        
    except Exception as e:
        return {"status": "error", "message": f"AI Audit failed: {str(e)}"}
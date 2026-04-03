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

def calculate_quantum_price(cpu_score, ram_score, net_score, hw_power=1.0):
    """
    Твоя величественная формула: Rate = (Base * ln(1 + C)) / H
    """
    base_rate = 0.0005  # Базовая цена в USDC
    total_complexity = cpu_score + ram_score + net_score
    
    if total_complexity == 0:
        return base_rate
        
    rate = (base_rate * math.log(1 + total_complexity)) / hw_power
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
        
        # Считаем цену по формуле
        price_per_sec = calculate_quantum_price(
            cpu_score=result.get("cpu", 1),
            ram_score=result.get("ram", 1),
            net_score=result.get("network", 0)
        )
        
        return {
            "status": "success",
            "scores": result,
            "calculated_rate_usd_sec": price_per_sec
        }
        
    except Exception as e:
        return {"status": "error", "message": f"AI Audit failed: {str(e)}"}
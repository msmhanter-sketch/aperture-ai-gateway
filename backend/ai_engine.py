import math
import json
from google import genai
from google.genai import types

# Сюда вставишь свой API ключ от Google Studio
GEMINI_API_KEY = "AIzaSyAyeW1ExJFlL_McxOxWIvRbQmFVPM7MurY"
client = genai.Client(api_key=GEMINI_API_KEY)

# Наша величественная формула
def calculate_quantum_price(cpu_score, ram_score, net_score, hw_power=1.0):
    base_rate = 0.0005 # Базовая цена в USDC
    total_complexity = cpu_score + ram_score + net_score
    
    # Формула: Rate = (Base * ln(1 + C)) / H
    if total_complexity == 0:
        return base_rate
        
    rate = (base_rate * math.log(1 + total_complexity)) / hw_power
    return round(rate, 6)

# Функция общения с Gemini 2.5 Flash
def analyze_code_complexity(code_snippet: str):
    prompt = f"""
    You are an expert AI code auditor for a DePIN compute network.
    Analyze the following Python code and estimate its resource complexity on a scale of 1 to 100 for three parameters: CPU, RAM, and Network.
    - CPU: Loops, math operations, recursion.
    - RAM: Large arrays, heavy imports (numpy, pandas).
    - Network: API calls, downloads.
    
    Respond ONLY in strict JSON format like this:
    {{"cpu": 10, "ram": 5, "network": 0, "reason": "Short explanation"}}
    
    Code to analyze:
    {code_snippet}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1 # Делаем его строгим и точным
            ),
        )
        
        # Парсим ответ от ИИ
        result = json.loads(response.text)
        
        # Считаем итоговую цену по нашей формуле
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
        return {"status": "error", "message": str(e)}

# --- ТЕСТОВЫЙ ЗАПУСК ---
if __name__ == "__main__":
    test_code = """
import numpy as np
for i in range(1000):
    for j in range(1000):
        matrix = np.random.rand(100, 100)
    """
    print("Отправляем код на суд ИИ...")
    result = analyze_code_complexity(test_code)
    print(json.dumps(result, indent=2))
import requests
import time
import uuid
import subprocess
import os
from pynvml import *

try:
    nvmlInit()
    handle = nvmlDeviceGetHandleByIndex(0)
    gpu_name = nvmlDeviceGetName(handle)
    vram_total = nvmlDeviceGetMemoryInfo(handle).total / (1024**3)
except Exception as e:
    gpu_name = "Unknown GPU"
    vram_total = 0.0

NODE_ID = f"node-{uuid.uuid4().hex[:6]}"
SERVER_URL = "http://localhost:8000"

def start_agent():
    print(f"--- Aperture Agent Started ---")
    print(f"Targeting: {gpu_name} ({vram_total:.2f} GB)")
    print(f"Node ID: {NODE_ID}")
    print("Listening for tasks... (Press Ctrl+C to stop)\n")

    payload = {
        "node_id": NODE_ID,
        "gpu_name": gpu_name,
        "vram_total": round(vram_total, 2),
        "status": "ONLINE"
    }

    while True:
        try:
            # 1. Отправляем сигнал "Я жив"
            requests.post(f"{SERVER_URL}/register_node", json=payload)
            
            # 2. Запрашиваем задачу
            task_res = requests.get(f"{SERVER_URL}/get_task").json()
            
            if task_res.get("task_id"):
                task_id = task_res["task_id"]
                code = task_res["code"]
                print(f"[*] Task caught: {task_id}. Executing locally...")
                
                # Сохраняем код во временный файл
                with open("temp_task.py", "w", encoding="utf-8") as f:
                    f.write(code)
                
                # Запускаем скрипт
                result = subprocess.run(
                    ["python", "temp_task.py"], 
                    capture_output=True, text=True
                )
                
                # Читаем вывод (или ошибку)
                output = result.stdout if result.returncode == 0 else result.stderr
                if not output:
                    output = "Code executed silently (no output)."
                
                # Отправляем результат обратно на сервер
                requests.post(f"{SERVER_URL}/submit_result", json={
                    "task_id": task_id,
                    "output": output
                })
                print(f"[+] Result for {task_id} sent back to Orchestrator.")
                
                # Убираем за собой мусор
                if os.path.exists("temp_task.py"):
                    os.remove("temp_task.py")
                
        except Exception as e:
            # Если сервер упал, просто ждем
            pass
            
        time.sleep(5) # Проверяем задачи каждые 5 секунд

if __name__ == "__main__":
    try:
        start_agent()
    except KeyboardInterrupt:
        print("\n[!] Agent stopped.")
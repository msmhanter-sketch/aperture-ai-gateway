import requests
import time
import subprocess
import os
import uuid
import sys
import threading

# --- CONFIG ---
API_URL = "http://127.0.0.1:8000"
NODE_ID = "APERTURE-COMPUTE-NODE-PRO"

def run_python_code_with_heartbeat(code: str, task_id: str, wallet: str = None):
    """
    Запускает код, читает вывод в реальном времени и проверяет баланс каждые 10 секунд.
    """
    temp_filename = f"task_{uuid.uuid4().hex[:8]}.py"
    with open(temp_filename, "w", encoding="utf-8") as f:
        f.write(code)

    start_time = time.perf_counter()
    output_lines = []
    
    print(f"⚙️ Launching process using: {sys.executable}")
    
    # Запускаем через Popen (не ждем окончания)
    process = subprocess.Popen(
        [sys.executable, temp_filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1, # Построчная буферизация
        universal_newlines=True,
        encoding="utf-8" # <--- ВОТ ОН, ФИКС ДЛЯ ЭМОДЗИ И РУССКОГО ЯЗЫКА!
    )

    # Функция для фонового чтения логов (чтобы не заблокировать основной поток)
    def reader():
        for line in iter(process.stdout.readline, ''):
            output_lines.append(line)
        process.stdout.close()

    # Запускаем чтение в отдельном потоке
    t = threading.Thread(target=reader)
    t.start()

    # ОСНОВНОЙ ЦИКЛ (Heartbeat)
    while t.is_alive():
        # Ждем 10 секунд или пока поток чтения не завершится
        t.join(timeout=10.0)
        
        # Если поток всё ещё жив (код всё ещё работает) -> проверяем пульс
        if t.is_alive():
            print(f"💓 [Heartbeat] Task {task_id} is running... Checking balance.")
            
            # Если бэкенд передал кошелек, проверяем его баланс
            if wallet:
                try:
                    res = requests.get(f"{API_URL}/balance/{wallet}", timeout=5)
                    if res.status_code == 200:
                        current_balance = res.json().get("balance", 0)
                        
                        # Если баланс упал ниже порога - УБИВАЕМ ПРОЦЕСС
                        if current_balance < 0.001:
                            print(f"🚨 [KILL] Task {task_id} terminated: Insufficient Funds.")
                            process.kill()
                            output_lines.append("\n\n🚨 STOPPED BY SENTINEL: Insufficient Gas (Balance < 0.001 SOL).\nPartial results saved above.")
                            break
                except Exception as e:
                    print(f"⚠️ [Heartbeat Error]: Could not reach backend: {e}")
                    
            # Ограничение по абсолютному времени (чтобы не висели часами)
            if time.perf_counter() - start_time > 300: # 5 минут максимум
                print(f"🚨 [KILL] Task {task_id} terminated: Timeout limit reached.")
                process.kill()
                output_lines.append("\n\n🚨 STOPPED: Max Execution Time (5 mins) Reached.")
                break

    execution_time = time.perf_counter() - start_time
    
    # Склеиваем весь вывод, который успели собрать
    full_output = "".join(output_lines)
    if not full_output:
        full_output = "Execution completed with no output (did you forget to print()?)."

    # Чистим за собой
    if os.path.exists(temp_filename):
        os.remove(temp_filename)

    return full_output, execution_time

def main():
    print(f"🚀 {NODE_ID} IS ONLINE. Searching for real AI payloads...")
    print(f"📂 Working directory: {os.getcwd()}")

    while True:
        try:
            # 1. Запрашиваем задачу у шлюза
            response = requests.get(f"{API_URL}/get_task")
            if response.status_code != 200:
                print(f"⚠️ Gateway unreachable (HTTP {response.status_code}). Retrying in 5s...")
                time.sleep(5)
                continue

            task = response.json()

            # Если в очереди есть задача
            if task.get("task_id"):
                task_id = task["task_id"]
                code = task["code"]
                wallet = task.get("wallet") # Получаем кошелек из задачи
                
                print("-" * 40)
                print(f"📦 RECEIVED TASK: {task_id}")
                print(f"🧠 EXECUTING PAYLOAD...")
                
                # 2. ЗАПУСКАЕМ С ПУЛЬСОМ
                raw_output, duration = run_python_code_with_heartbeat(code, task_id, wallet)
                
                # 3. ПОДГОТОВКА ДАННЫХ ДЛЯ ФРОНТЕНДА
                lines = raw_output.splitlines()
                display_output = raw_output
                
                if len(lines) > 10:
                    display_output = "\n".join(lines[:10])
                    display_output += f"\n\n[📊] OUTPUT TRUNCATED. Total lines: {len(lines)}"
                
                with open(f"node_log_{task_id}.txt", "w", encoding="utf-8") as f:
                    f.write(raw_output)

                # 4. ОТПРАВЛЯЕМ РЕЗУЛЬТАТ В БЭКЕНД
                payload = {
                    "task_id": task_id,
                    "output": display_output,
                    "execution_time": round(duration, 6),
                    "full_log": raw_output 
                }
                
                res = requests.post(f"{API_URL}/submit_result", json=payload)
                
                if res.status_code == 200:
                    print(f"✅ TASK SETTLED: {task_id} in {duration:.4f}s")
                else:
                    print(f"❌ SETTLEMENT FAILED: {res.text}")

            else:
                pass # Очередь пуста

        except Exception as e:
            print(f"🚨 Worker Loop Error: {e}")
            time.sleep(2)

        time.sleep(1)

if __name__ == "__main__":
    main()
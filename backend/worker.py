import requests
import time
import subprocess
import os
import uuid
import sys # Добавили для автоматического поиска пути к Python

# --- CONFIG ---
API_URL = "http://127.0.0.1:8000"
NODE_ID = "APERTURE-COMPUTE-NODE-PRO"

def run_python_code(code: str):
    """
    Запускает присланный код в изолированном процессе.
    Использует sys.executable для совместимости с Windows/Linux.
    """
    # Создаем уникальный файл для этой конкретной задачи
    temp_filename = f"task_{uuid.uuid4().hex[:8]}.py"
    
    # Сохраняем код в файл с кодировкой utf-8
    with open(temp_filename, "w", encoding="utf-8") as f:
        f.write(code)

    start_time = time.perf_counter()
    
    try:
        print(f"⚙️ Launching process using: {sys.executable}")
        
        # subprocess.run запускает код. 
        # sys.executable — это путь к твоему текущему интерпретатору Python.
        result = subprocess.run(
            [sys.executable, temp_filename],
            capture_output=True,
            text=True,
            timeout=30 # Защита от бесконечных циклов
        )
        
        execution_time = time.perf_counter() - start_time
        
        # Собираем стандартный вывод и ошибки (stderr)
        full_output = result.stdout
        if result.stderr:
            full_output += f"\n--- RUNTIME ERRORS ---\n{result.stderr}"
            
        if not full_output:
            full_output = "Execution completed with no output (did you forget to print()?)."
            
        return full_output, execution_time

    except subprocess.TimeoutExpired:
        # Если код работает дольше 30 секунд — убиваем задачу
        return "🚨 ERROR: Execution timed out (Limit: 30s). Process terminated to save resources.", 30.0
    except Exception as e:
        return f"🚨 CRITICAL NODE ERROR: {str(e)}", 0.0
    finally:
        # Обязательно удаляем временный файл, чтобы не мусорить на диске
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

def main():
    print(f"🚀 {NODE_ID} IS ONLINE. Searching for real AI payloads...")
    print(f"📂 Working directory: {os.getcwd()}")

    while True:
        try:
            # 1. Запрашиваем новую задачу у шлюза (Backend)
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
                
                print("-" * 40)
                print(f"📦 RECEIVED TASK: {task_id}")
                print(f"🧠 EXECUTING PAYLOAD...")
                
                # 2. ЗАПУСКАЕМ РЕАЛЬНОЕ ВЫПОЛНЕНИЕ КОДА
                raw_output, duration = run_python_code(code)
                
                # 3. ПОДГОТОВКА ДАННЫХ ДЛЯ ФРОНТЕНДА
                lines = raw_output.splitlines()
                display_output = raw_output
                
                # Если вывод слишком длинный (>10 строк), добавляем метку для скачивания
                if len(lines) > 10:
                    display_output = "\n".join(lines[:10])
                    display_output += f"\n\n[📊] OUTPUT TRUNCATED. Total lines: {len(lines)}"
                
                # Сохраняем локальный лог на ноде (на всякий случай для отладки)
                with open(f"node_log_{task_id}.txt", "w", encoding="utf-8") as f:
                    f.write(raw_output)

                # 4. ОТПРАВЛЯЕМ РЕЗУЛЬТАТ В БЭКЕНД
                # Мы шлем display_output с меткой [📊], чтобы Dashboard.jsx показал ссылку на скачивание
                payload = {
                    "task_id": task_id,
                    "output": display_output,
                    "execution_time": round(duration, 6)
                }
                
                # ВАЖНО: Добавляем поле для хранения полного лога в базе (если ты обновил main.py)
                payload["full_log"] = raw_output 
                
                res = requests.post(f"{API_URL}/submit_result", json=payload)
                
                if res.status_code == 200:
                    print(f"✅ TASK SETTLED: {task_id} in {duration:.4f}s")
                else:
                    print(f"❌ SETTLEMENT FAILED: {res.text}")

            else:
                # Очередь пуста, ждем 1 секунду
                pass

        except Exception as e:
            print(f"🚨 Worker Loop Error: {e}")
            time.sleep(2)

        time.sleep(1)

if __name__ == "__main__":
    main()
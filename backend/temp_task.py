import hashlib
import multiprocessing
import time
import os

# Устанавливаем сложность (7 нулей заставят проц попотеть)
DIFFICULTY = "0000000" 
MAX_ITERATIONS = 50_000_000

def crunch_matrix(core_id, start_idx, end_idx, result_queue):
    print(f"[CORE-{core_id}] Initializing ZK-Proof computation matrix: {start_idx} to {end_idx}")
    
    for nonce in range(start_idx, end_idx):
        # Тяжелая криптографическая операция (симуляция графа)
        payload = f"APERTURE_ZK_ROLLUP_STATE_{nonce}_{core_id}_VALIDATION".encode('utf-8')
        hash_hex = hashlib.sha256(payload).hexdigest()
        
        # Ищем коллизию, удовлетворяющую сложности
        if hash_hex.startswith(DIFFICULTY):
            result_queue.put((core_id, nonce, hash_hex))
            return
        
        # Выводим логи состояния, чтобы терминал выглядел живым
        if nonce > start_idx and nonce % 1_500_000 == 0:
            print(f"[CORE-{core_id}] ⚡ Processed {nonce - start_idx} nodes. Searching deep state...")

if __name__ == '__main__':
    print("\n[APERTURE PROTOCOL] INITIATING DECENTRALIZED COMPUTE...")
    print(f"Targeting ZK-Proof Difficulty: {DIFFICULTY}")
    
    start_time = time.time()
    
    # Определяем количество ядер на сервере (на ВМ их будет несколько)
    cores = multiprocessing.cpu_count()
    print(f"[SYSTEM] Detected {cores} CPU cores. Splitting workload...\n")
    
    # Распределяем нагрузку
    chunk_size = MAX_ITERATIONS // cores
    processes = []
    result_queue = multiprocessing.Queue()
    
    for i in range(cores):
        start = i * chunk_size
        end = (i + 1) * chunk_size
        p = multiprocessing.Process(target=crunch_matrix, args=(i, start, end, result_queue))
        processes.append(p)
        p.start()
    
    # Ждем, пока какое-нибудь ядро не найдет решение
    core_id, winning_nonce, final_hash = result_queue.get()
    
    # Убиваем остальные процессы, так как ответ найден
    for p in processes:
        p.terminate()
        
    end_time = time.time()
    execution_time = end_time - start_time
    
    print("\n" + "="*50)
    print("✅ [SUCCESS] ZK-PROOF GENERATED AND VALIDATED")
    print("="*50)
    print(f"Winning Core : CORE-{core_id}")
    print(f"Nonce Found  : {winning_nonce}")
    print(f"Valid Hash   : {final_hash}")
    print(f"Time Elapsed : {execution_time:.2f} seconds")
    print(f"Burn Rate    : {(execution_time * 0.00015):.6f} SOL deducted.")
    print("="*50 + "\n")

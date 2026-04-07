🛠 Installation & Deployment Guide: Aperture AI
This guide provides a step-by-step walkthrough to deploy the Aperture AI ecosystem. As a high-performance DePIN grid, the system requires a distributed setup across three main layers: the Solana smart contract, the AI-Sentinel Oracle, and the Compute Worker.
+3

1. Prerequisites
Before starting, ensure your environment meets these requirements:


Solana Tool Suite & Anchor Framework (Latest stable) 


Rust (Latest) 


Python 3.10+ (With pip and venv) 


Node.js v18+ & npm/yarn 
+1

2. Smart Contract Deployment (Solana Devnet)
The core logic resides in the programs directory.

Navigate to programs:
cd programs

Build the Anchor program:
anchor build

Deploy to Devnet:
anchor deploy


Note: Ensure your Anchor.toml and wallet are configured for Solana Devnet. 

3. The Multi-Terminal Setup (Running the Grid)
To demonstrate the full autonomous lifecycle, you must run the following three components in separate terminal instances.
+1

🔵 Terminal 1: AI-Sentinel Oracle (The Brain)
This FastAPI-based backend performs pre-execution audits and emits pricing signals.
+2

Navigate to backend:
cd backend

Setup environment:


python -m venv venv 
source venv/bin/activate (Windows: venv\Scripts\activate)
pip install -r requirements.txt

Launch the Oracle:


uvicorn main:app --reload --port 8000 

🟠 Terminal 2: God-Mode Compute Worker (Execution Layer)
This worker handles the heavy algorithmic lifting, utilizing NumPy for complexity metrics and telemetry.
+1

Activate environment (in the backend folder):
source venv/bin/activate

Launch the Worker:
python worker.py


The worker will now wait for audited payloads to execute in an isolated environment. 

🟢 Terminal 3: Frontend Dashboard (Command Center)
The Next.js interface for payload submission and real-time telemetry.

Navigate to frontend:
cd frontend

Install & Start:
npm install
npm run dev


Access UI: Open http://localhost:3000.

🔄 Verified Execution Workflow

Submit Payload: Upload a Python script via the Dashboard.


AI Audit: Terminal 1 (Sentinel) intercepts the code, evaluates complexity using algorithmic metrics, and signs the price signal.
+1


On-Chain Settlement: The smart contract updates the burn rate autonomously on Solana.
+1


Compute: Terminal 2 (Worker) executes the task and streams telemetry back to the UI.
+1


Built by Nemezida (Solo Build) for the National Solana Hackathon. Supported by Superteam KZ 🇰🇿 
+2

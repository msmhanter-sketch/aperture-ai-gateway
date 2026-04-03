# 🚀 Aperture: Autonomous AI-Gateway for Compute & API Monetization

## ⚠️ The Problem
Web3 and Web2 API monetization is broken. Developers are forced to use static subscription models ($10/mo) or fixed pay-per-call rates. But compute isn't static. One API call might be a simple `print("hello")`, while another triggers a massive multi-endpoint AI inference and complex O(n²) algorithms. Flat rates lead to either server drain or overcharging users. 

## 💡 The Solution: Aperture
Aperture is an autonomous smart contract gateway powered by an off-chain AI agent. 
Instead of static fees, users open a micro-payment stream on Solana. Before executing a request, our AI agent dynamically evaluates the algorithmic complexity and external API load of the user's payload. It then autonomously updates the smart contract's token burn rate (fee-per-second) in real-time. 

You pay exactly for the compute you consume. Not a cent more.

## ⚙️ Architecture (Solana Only)
This high-frequency dynamic pricing is **only possible on Solana**. Updating the state (burn rate) dynamically every few seconds would cost hundreds of dollars in gas on Ethereum. On Solana, it costs fractions of a cent.

1. **User** deposits USDC into the `Aperture` Anchor program.
2. **User** sends a payload/request to the Developer's backend.
3. **AI Agent (Off-chain)** analyzes the request complexity (Big O, payload weight, external API hops).
4. **AI Agent** pushes an on-chain transaction updating the user's specific `burn_rate` via CPI.
5. **Aperture Contract** streams micro-payments based on the dynamic AI-assigned rate while the compute runs.
6. Once completed, the rate resets to zero.

## 🛠 Tech Stack
- **Smart Contract:** Rust / Anchor Framework
- **AI Agent & Backend:** Python / FastAPI / LLM Complexity Evaluation
- **Frontend:** Next.js / Tailwind

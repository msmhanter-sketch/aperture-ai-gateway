import React, { useState, useEffect, useRef } from 'react';
import { useWallet, useConnection } from '@solana/wallet-adapter-react';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';
import { Transaction, SystemProgram, LAMPORTS_PER_SOL, PublicKey } from '@solana/web3.js';

const API_URL = 'http://127.0.0.1:8000';
// Сюда вставь адрес, на который будут приходить тестовые SOL
const TREASURY_WALLET = "ВАШ_АДРЕС_SOL_ИЗ_SOLFLARE"; 

export default function Gateway() {
  const { publicKey, connected, sendTransaction } = useWallet();
  const { connection } = useConnection();
  const [balance, setBalance] = useState(0);
  const [isDemo, setIsDemo] = useState(false);
  const [logs, setLogs] = useState([{ msg: "> System initialized. Waiting for payload...", type: "system" }]);
  const [code, setCode] = useState(`# Write your Python payload here\nimport numpy as np\n\nfor i in range(100):\n    print("Aperture is running")`);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  
  const terminalRef = useRef(null);

  const [guestId] = useState(() => {
    let id = localStorage.getItem('aperture_guest_id');
    if (!id) {
      id = 'guest_' + Math.random().toString(36).substring(2, 10);
      localStorage.setItem('aperture_guest_id', id);
    }
    return id;
  });

  const addLog = (msg, type = "info") => {
    setLogs(prev => [...prev, { msg: `> ${msg}`, type }]);
  };

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  // Функция загрузки баланса
  const fetchBalance = async () => {
    try {
      const walletAddr = connected && publicKey ? publicKey.toString() : null;
      const url = walletAddr 
        ? `${API_URL}/balance?wallet=${walletAddr}&guest_id=${guestId}`
        : `${API_URL}/balance?guest_id=${guestId}`;

      const response = await fetch(url);
      const data = await response.json();
      
      setBalance(data.balance);
      setIsDemo(data.is_demo && !walletAddr);
    } catch (error) {
      addLog("Connection to Gateway failed.", "error");
    }
  };

  useEffect(() => {
    fetchBalance();
    if (connected && publicKey) {
        addLog(`Web3 Identity synced: ${publicKey.toString().slice(0, 4)}...${publicKey.toString().slice(-4)}`, "success");
    }
  }, [connected, publicKey, guestId]);

  // МАГИЯ SOLANA: Реальное пополнение через транзакцию
  const handleTopUp = async () => {
    if (!connected || !publicKey) return addLog("Connect wallet first!", "error");
    
    try {
      addLog("Initiating transaction (0.01 SOL)...", "system");
      
      const transaction = new Transaction().add(
        SystemProgram.transfer({
          fromPubkey: publicKey,
          toPubkey: new PublicKey(TREASURY_WALLET),
          lamports: 0.01 * LAMPORTS_PER_SOL, 
        })
      );

      const signature = await sendTransaction(transaction, connection);
      addLog(`Transaction sent! Sig: ${signature.slice(0, 8)}...`, "info");
      addLog("Verifying on-chain...", "system");

      // Стучимся на бэкенд, чтобы он подтвердил оплату
      const response = await fetch(`${API_URL}/verify-payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          signature: signature,
          wallet: publicKey.toString()
        })
      });

      const result = await response.json();
      if (response.ok) {
        setBalance(result.new_balance);
        addLog(`Top-up successful! New balance: ${result.new_balance} USDC`, "success");
      } else {
        addLog("Payment verification failed.", "error");
      }
    } catch (error) {
      addLog(`Transaction failed: ${error.message}`, "error");
    }
  };

  const handleExecute = async () => {
    if (!code.trim()) return addLog("Payload is empty.", "error");

    setIsAnalyzing(true);
    addLog("Sending payload to AI-Auditor...", "system");

    try {
      const walletAddr = connected && publicKey ? publicKey.toString() : null;
      const response = await fetch(`${API_URL}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          code: code, 
          guest_id: walletAddr ? null : guestId,
          wallet: walletAddr 
        })
      });

      const result = await response.json();

      if (response.ok) {
        addLog(`AI Analysis complete. CPU: ${result.ai_analysis.cpu}, RAM: ${result.ai_analysis.ram}`, "info");
        addLog(`Reason: ${result.ai_analysis.reason}`, "info");
        addLog(`Cost: ${result.cost} USDC. Execution Approved.`, "success");
        setBalance(result.new_balance);
      } else {
        const errorMsg = typeof result.detail === 'object' ? JSON.stringify(result.detail) : result.detail;
        addLog(`Gateway Error: ${errorMsg}`, "error");
      }
    } catch (error) {
      addLog(`Network error: ${error.message}`, "error");
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="container">
      <header>
        <div className="logo">
          <h1>APERTURE <span>v1.0</span></h1>
          <p>Quantum Pricing DePIN Gateway</p>
        </div>
        <div className="wallet-panel">
          <div className="balance-box">
            <span className="label">Balance:</span>
            <span id="balance-display">{balance.toFixed(4)}</span> <span className="currency">USDC</span>
            {isDemo && <div className="badge">DEMO MODE</div>}
            {connected && (
              <button onClick={handleTopUp} className="btn-topup">
                Top Up
              </button>
            )}
          </div>
          <WalletMultiButton className="solana-btn" />
        </div>
      </header>

      <main>
        <div className="editor-section">
          <div className="section-header">
            <h2>Target Payload (Python)</h2>
            <span className="status-dot green"></span>
          </div>
          <textarea 
            value={code} 
            onChange={(e) => setCode(e.target.value)}
            spellCheck="false"
          />
          <button 
            className="btn primary" 
            onClick={handleExecute} 
            disabled={isAnalyzing}
          >
            {isAnalyzing ? "Analyzing..." : "Deploy & Execute"}
          </button>
        </div>

        <div className="terminal-section">
          <div className="section-header">
            <h2>Gateway Terminal</h2>
          </div>
          <div className="terminal-content" ref={terminalRef}>
            {logs.map((log, i) => (
              <div key={i} className={`log ${log.type}`}>{log.msg}</div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
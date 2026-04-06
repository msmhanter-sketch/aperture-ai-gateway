import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useWallet, useConnection } from '@solana/wallet-adapter-react';
import { useWalletModal } from '@solana/wallet-adapter-react-ui';
import { LAMPORTS_PER_SOL, Transaction, SystemProgram, PublicKey } from '@solana/web3.js';

// Подключаем логотип
import logo from './assets/logo.png';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const TREASURY = "8KhV8aMHmofqPreou1wkf2PtbbYNTSWDyekSZALsEvh2";

const Dashboard = () => {
  const [walletBalance, setWalletBalance] = useState(0); 
  const [internalBalance, setInternalBalance] = useState(0.0); 
  const [customDeposit, setCustomDeposit] = useState(0.5);
  const [burnRate, setBurnRate] = useState(0); 
  const [solPrice, setSolPrice] = useState(null); 
  const [code, setCode] = useState(`# Aperture AI Payload\nimport time\nimport math\n\nprint("--- Starting Complex Calculation ---")\nfor i in range(1, 6):\n    print(f"Step {i}: Factorial of {i*5} is {math.factorial(i*5)}")\n    time.sleep(0.5)\nprint("--- Execution Complete ---")`);
  const [status, setStatus] = useState('IDLE'); 
  const [logs, setLogs] = useState([]);
  const [currentTaskId, setCurrentTaskId] = useState(null); 
  
  const terminalEndRef = useRef(null);
  const fileInputRef = useRef(null); 
  const { publicKey, sendTransaction, signMessage, disconnect } = useWallet();
  const { connection } = useConnection();
  const { setVisible } = useWalletModal(); 

  const addLog = (msg) => setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const fetchPrice = async () => {
    try {
      const res = await axios.get(`${API_URL}/price`); 
      if (res.data.price) setSolPrice(res.data.price);
    } catch (e) {
      if(!solPrice) setSolPrice(182.45); 
    }
  };

  useEffect(() => {
    fetchPrice();
    const interval = setInterval(fetchPrice, 10000);
    return () => clearInterval(interval);
  }, []);

  const syncBalances = async () => {
    if (!publicKey) return;
    try {
      const bal = await connection.getBalance(publicKey);
      setWalletBalance(bal / LAMPORTS_PER_SOL);
      const res = await axios.get(`${API_URL}/balance/${publicKey.toBase58()}`);
      setInternalBalance(res.data.balance);
    } catch (e) { console.error("Sync failed", e); }
  };

  useEffect(() => { syncBalances(); }, [publicKey]);

  // Визуальное списание топлива на фронте
  useEffect(() => {
    let timer;
    if (status === 'RUNNING' && burnRate > 0) {
      timer = setInterval(() => {
        setInternalBalance(prev => Math.max(0, prev - (burnRate / 10)));
      }, 100);
    }
    return () => clearInterval(timer);
  }, [status, burnRate]);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      setCode(evt.target.result);
      addLog(`📁 Script Loaded: ${file.name}`);
    };
    reader.readAsText(file);
  };

  const deposit = async (amount) => {
    if (!publicKey) return setVisible(true);
    try {
      addLog(`⛽ Refilling: ${amount} SOL...`);
      const tx = new Transaction().add(SystemProgram.transfer({
        fromPubkey: publicKey,
        toPubkey: new PublicKey(TREASURY),
        lamports: Math.round(amount * LAMPORTS_PER_SOL),
      }));
      const sig = await sendTransaction(tx, connection);
      await connection.confirmTransaction(sig, 'confirmed');
      const res = await axios.post(`${API_URL}/deposit`, { wallet: publicKey.toBase58(), amount: amount, signature: sig });
      setInternalBalance(res.data.new_balance);
      addLog(`💰 Tank Refilled!`);
      syncBalances();
    } catch (e) {
      addLog(`❌ Transaction Error.`);
    }
  };

  const stopTask = async () => {
    if (!currentTaskId) return;
    try {
      await axios.post(`${API_URL}/stop/${currentTaskId}`);
      addLog('🛑 Aborted by user.');
    } catch (e) {} finally {
      setStatus('IDLE');
      setBurnRate(0);
      setCurrentTaskId(null);
      syncBalances();
    }
  };

  const runTask = async () => {
    if (!publicKey) return setVisible(true);
    
    // СНИЖАЕМ ПОРОГ: Теперь пускаем даже с 0.002 SOL
    // Это покроет Audit Fee (0.001) и даст ~15 минут работы на низком burn_rate
    if (internalBalance < 0.002) {
        addLog("⚠️ Fuel Low (min 0.002 SOL)");
        return;
    }

    setStatus('RUNNING');
    addLog('🧠 AI Sentinel Audit starting...');
    
    const message = "Sign to authenticate execution.";
    const signature = await signMessage(new TextEncoder().encode(message));

    try {
      const res = await axios.post(`${API_URL}/execute`, {
        code: code,
        wallet: publicKey.toBase58(),
        signature: Array.from(signature),
        message: message
      });
      
      const { task_id, burn_rate, startup_fee_paid, on_chain_proof } = res.data;
      
      setBurnRate(burn_rate);
      setCurrentTaskId(task_id);

      addLog(`🎟️ Audit Fee: ${startup_fee_paid} SOL paid.`);
      addLog(`🔥 Burn Rate: ${burn_rate.toFixed(8)} SOL/sec`);
      addLog(`🚀 Execution Started. ID: ${task_id.slice(0,8)}`);
      
      if (on_chain_proof) {
          console.log("On-chain proof:", on_chain_proof);
      }

      const poll = setInterval(async () => {
        try {
          const r = await axios.get(`${API_URL}/result/${task_id}`);
          
          if (r.data.status === 'completed') {
            clearInterval(poll);
            setStatus('IDLE');
            setBurnRate(0);
            
            addLog(`✅ Task Finished Successfully.`);
            
            if (r.data.output) {
                const lines = r.data.output.split('\n');
                lines.forEach(line => {
                    if (line.trim()) addLog(`> ${line}`);
                });
            }
            
            addLog(`🧾 Compute Receipt Generated.`);
            syncBalances();
          }
        } catch (e) {
            console.error("Polling error", e);
        }
      }, 1000);
      
    } catch (e) {
      addLog(`❌ AI Firewall Blocked execution.`);
      setStatus('IDLE');
    }
  };

  const containerStyle = {
    backgroundColor: '#fafafa',
    backgroundImage: 'linear-gradient(to right, #e5e7eb 1px, transparent 1px), linear-gradient(to bottom, #e5e7eb 1px, transparent 1px)',
    backgroundSize: '40px 40px',
    minHeight: '100vh',
    height: 'auto',
    overflowY: 'visible', 
    fontFamily: '"Inter", sans-serif',
    color: '#0F172A',
    display: 'block',
    position: 'relative'
  };

  const cardStyle = {
    background: '#FFFFFF',
    borderRadius: '24px',
    border: '1px solid #E2E8F0',
    boxShadow: '0 12px 40px rgba(0, 0, 0, 0.03)',
    padding: '30px'
  };

  const purpleBtn = {
    backgroundColor: '#6D28D9',
    color: '#FFF',
    border: 'none',
    borderRadius: '12px',
    fontWeight: '700',
    cursor: 'pointer',
    transition: '0.2s'
  };

  return (
    <div style={containerStyle}>
      <style>{`
        html, body, #root { 
          height: auto !important; 
          overflow: visible !important; 
          margin: 0; padding: 0;
        }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-thumb { background: #E2E8F0; borderRadius: 10px; }
      `}</style>
      
      <header style={{ 
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
        padding: '20px 40px', borderBottom: '1px solid rgba(0,0,0,0.05)',
        background: 'rgba(255, 255, 255, 0.8)', backdropFilter: 'blur(12px)',
        position: 'relative', zIndex: 50
      }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <img src={logo} alt="Aperture" style={{ height: '56px', width: 'auto', display: 'block' }} />
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '30px' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '10px', color: '#94A3B8', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '1px' }}>Gas Tank</div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: '#6D28D9' }}>{internalBalance.toFixed(5)} SOL</div>
          </div>
          <button 
            onClick={() => publicKey ? disconnect() : setVisible(true)} 
            style={{ ...purpleBtn, padding: '12px 24px', fontSize: '14px', boxShadow: '0 4px 15px rgba(109, 40, 217, 0.2)' }}
          >
            {publicKey ? 'DISCONNECT' : 'CONNECT'}
          </button>
        </div>
      </header>

      <main style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '40px', padding: '60px 40px 100px 40px' }}>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
          <div style={{ ...cardStyle, padding: '0', overflow: 'hidden' }}>
            <div style={{ padding: '18px 30px', background: '#F8FAFC', borderBottom: '1px solid #F1F5F9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '11px', fontWeight: '800', color: '#64748B' }}>COMPUTE_ENGINE_V1</span>
                {solPrice && <span style={{ fontSize: '11px', fontWeight: '800', color: '#10B981' }}>ORACLE: ${solPrice.toFixed(2)}</span>}
            </div>
            <textarea 
                value={code} 
                onChange={e => setCode(e.target.value)} 
                style={{ width: '100%', height: '420px', backgroundColor: '#F8FAFC', color: '#1E293B', padding: '35px', border: 'none', outline: 'none', fontSize: '15px', fontFamily: "'Fira Code', monospace", lineHeight: '1.7', resize: 'none' }} 
            />
          </div>

          <div style={{ display: 'flex', gap: '20px' }}>
            <input type="file" ref={fileInputRef} onChange={handleFileUpload} style={{ display: 'none' }} />
            <button 
                onClick={() => fileInputRef.current.click()} 
                style={{ flex: '0.4', padding: '20px', borderRadius: '16px', border: '1.5px solid #E2E8F0', background: '#FFF', color: '#111', fontWeight: '700', cursor: 'pointer', fontSize: '14px' }}
            >
                Import Script
            </button>
            <button 
                onClick={runTask} 
                disabled={status !== 'IDLE'} 
                style={{ flex: '1', padding: '20px', ...purpleBtn, fontSize: '16px', background: status === 'IDLE' ? '#6D28D9' : '#F1F5F9', color: status === 'IDLE' ? '#FFF' : '#94A3B8' }}
            >
                {status === 'IDLE' ? 'Initiate Compute' : 'Executing...'}
            </button>
            {status === 'RUNNING' && <button onClick={stopTask} style={{ padding: '0 25px', borderRadius: '16px', border: '1.5px solid #FEE2E2', color: '#EF4444', background: '#FFF', fontWeight: '700', cursor: 'pointer' }}>Stop</button>}
          </div>

          <div style={{ ...cardStyle, height: '250px', overflowY: 'auto', background: '#F8FAFC', border: '1px solid #F1F5F9', boxShadow: 'none' }}>
            <div style={{ fontSize: '10px', fontWeight: '900', color: '#CBD5E1', marginBottom: '15px', textTransform: 'uppercase', letterSpacing: '1px' }}>Autonomous System Stream</div>
            {logs.map((l, i) => (
                <div key={i} style={{ 
                    fontSize: '13px', 
                    marginBottom: '8px', 
                    color: l.includes('>') ? '#2DD4BF' : (l.includes('✅') ? '#10B981' : (l.includes('❌') ? '#EF4444' : '#475569')), 
                    fontFamily: 'monospace', 
                    borderBottom: '1px solid rgba(0,0,0,0.02)', 
                    paddingBottom: '4px' 
                }}>
                    {l}
                    {l.includes('[📊] OUTPUT TRUNCATED') && (
                      <a 
                          href={`${API_URL}/download/${currentTaskId}`} 
                          target="_blank" 
                          rel="noreferrer"
                          style={{ 
                              marginLeft: '10px', 
                              color: '#6D28D9', 
                              fontWeight: '800', 
                              textDecoration: 'underline', 
                              cursor: 'pointer',
                              fontSize: '11px'
                          }}
                      >
                          Download Full Log (.txt)
                      </a>
                    )}
                </div>
            ))}
            <div ref={terminalEndRef} />
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
          <div style={cardStyle}>
            <h3 style={{ fontSize: '16px', fontWeight: '800', marginBottom: '10px' }}>Refill Tank</h3>
            <p style={{ fontSize: '12px', color: '#94A3B8', marginBottom: '25px', lineHeight: '1.5' }}>Load credits to power decentralized AI compute tasks.</p>
            <div style={{ position: 'relative', marginBottom: '20px' }}>
                <input type="number" value={customDeposit} onChange={e => setCustomDeposit(e.target.value)} style={{ width: '100%', padding: '18px', borderRadius: '14px', border: '1.5px solid #E2E8F0', outline: 'none', fontSize: '18px', fontWeight: '800', color: '#000' }} />
                <span style={{ position: 'absolute', right: '18px', top: '50%', transform: 'translateY(-50%)', fontWeight: '900', color: '#475569', background: '#F1F5F9', padding: '6px 12px', borderRadius: '8px', fontSize: '12px', border: '1px solid #E2E8F0' }}>SOL</span>
            </div>
            <button onClick={() => deposit(parseFloat(customDeposit))} style={{ width: '100%', padding: '18px', ...purpleBtn, fontSize: '14px' }}>Confirm Deposit</button>
          </div>

          <div style={{ ...cardStyle, textAlign: 'center', background: '#F8FAFC', border: '1px solid #F1F5F9', boxShadow: 'none' }}>
            <div style={{ fontSize: '11px', fontWeight: '800', color: '#94A3B8', marginBottom: '8px', textTransform: 'uppercase' }}>Connected Wallet</div>
            <div style={{ fontSize: '22px', fontWeight: '900', color: '#111' }}>{walletBalance.toFixed(4)} <span style={{fontSize: '12px', color: '#CBD5E1'}}>SOL</span></div>
            <button onClick={() => publicKey ? disconnect() : setVisible(true)} style={{ marginTop: '12px', background: 'none', border: 'none', color: '#6D28D9', fontWeight: '800', fontSize: '12px', cursor: 'pointer', textDecoration: 'underline' }}>Switch Wallet</button>
          </div>

          <div style={{ borderRadius: '24px', border: '1.5px dashed #CBD5E1', padding: '35px', textAlign: 'center' }}>
             <button onClick={() => alert("Registration Locked")} style={{ background: 'none', border: 'none', color: '#94A3B8', fontWeight: '800', fontSize: '13px', cursor: 'pointer', textDecoration: 'underline' }}>Register Node Provider</button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
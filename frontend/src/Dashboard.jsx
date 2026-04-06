import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useWallet, useConnection } from '@solana/wallet-adapter-react';
import { useWalletModal } from '@solana/wallet-adapter-react-ui';
import { LAMPORTS_PER_SOL } from '@solana/web3.js';

const API_URL = 'http://127.0.0.1:8000';

const Dashboard = () => {
  const [balance, setBalance] = useState(0); 
  const [creditBalance, setCreditBalance] = useState(0.01); 
  const [burnRate, setBurnRate] = useState(0); 
  const [code, setCode] = useState(`# Aperture AI Payload\nprint("Connecting to RTX 3050...")\nimport math\nprint(f"Calculation: {math.sqrt(256)}")`);
  const [status, setStatus] = useState('IDLE'); 
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [logs, setLogs] = useState([]);
  const [activeNode, setActiveNode] = useState(null);
  const terminalEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const { publicKey, wallet } = useWallet();
  const { connection } = useConnection();
  const { setVisible } = useWalletModal(); 

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      setCode(e.target.result);
      addLog(`📁 File loaded: ${file.name}`);
    };
    reader.readAsText(file);
  };

  const stopTask = async () => {
    if (!currentTaskId) return;
    try {
      addLog('🛑 Sending termination signal to gateway...');
      await axios.post(`${API_URL}/stop/${currentTaskId}`);
      setStatus('IDLE');
      setBurnRate(0);
      setCurrentTaskId(null);
      addLog('⚠️ Execution aborted by user. Compute credits settled.');
      const finalBalRes = await axios.get(`${API_URL}/balance/${publicKey.toBase58()}`);
      setCreditBalance(finalBalRes.data.balance);
    } catch (e) {
      addLog('❌ Failed to terminate task.');
    }
  };

  useEffect(() => {
    let timer;
    if (status === 'EXECUTING' && burnRate > 0) {
      timer = setInterval(() => {
        setCreditBalance(prev => Math.max(0, (Number(prev) || 0) - (Number(burnRate) / 10)));
      }, 100);
    }
    return () => clearInterval(timer);
  }, [status, burnRate]);

  useEffect(() => {
    if (publicKey) {
      connection.getBalance(publicKey).then((bal) => setBalance(bal / LAMPORTS_PER_SOL));
      axios.get(`${API_URL}/balance/${publicKey.toBase58()}`).then((res) => {
        if (res.data && res.data.balance !== undefined) setCreditBalance(res.data.balance);
      }).catch(() => {});
    }
  }, [publicKey, connection]);

  useEffect(() => {
    const checkNodes = async () => {
      try {
        const res = await axios.get(`${API_URL}/active_nodes`);
        if (res.data.length > 0) setActiveNode(res.data[0]);
      } catch (e) {}
    };
    const interval = setInterval(checkNodes, 5000);
    return () => clearInterval(interval);
  }, []);

  const addLog = (msg) => {
    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  const runTask = async () => {
    if (!code.trim() || !publicKey) return;
    setStatus('DEPLOYING');
    setLogs([]);
    addLog('🛡️ SENTINEL: Starting deep security audit...');

    try {
      const response = await axios.post(`${API_URL}/execute`, {
        code: code,
        wallet: publicKey.toBase58() 
      });

      // 🔥 ИСПРАВЛЕНО: Достаем burn_rate и используем ЕГО ЖЕ
      const { task_id, burn_rate } = response.data;
      const bal = response.data.current_balance !== undefined ? response.data.current_balance : response.data.new_balance;
      
      setCurrentTaskId(task_id);
      if (bal !== undefined) setCreditBalance(bal);
      setBurnRate(burn_rate); // <-- Теперь всё четко

      addLog(`✅ Audit passed. Expected Rate: ${Number(burn_rate).toFixed(6)} CRD/sec`); 
      setStatus('EXECUTING');

      const poll = setInterval(async () => {
        try {
          const res = await axios.get(`${API_URL}/result/${task_id}`);
          if (res.data.status === 'completed') {
            clearInterval(poll);
            setStatus('IDLE');
            setBurnRate(0); 
            setCurrentTaskId(null);

            addLog(`🚀 NODE FINISHED.`);
            addLog(`>>> OUTPUT:\n${res.data.output}`);
            
            const finalBalRes = await axios.get(`${API_URL}/balance/${publicKey.toBase58()}`);
            if (finalBalRes.data && finalBalRes.data.balance !== undefined) {
              const actualBalance = finalBalRes.data.balance;
              setCreditBalance(prevVisualBalance => {
                const diff = actualBalance - prevVisualBalance;
                if (diff < -0.0005) {
                  addLog(`⚠️ ALERT: Aperture Penalty Scale (APS) triggered!`);
                  addLog(`📉 Sudden load detected. Penalty applied: ${Math.abs(diff).toFixed(6)} CRD`);
                } else if (diff > 0) {
                  addLog(`💸 SETTLEMENT: Unused gas refunded (+${diff.toFixed(6)} CRD)`);
                }
                return actualBalance; 
              });
            }
          }
        } catch (e) {}
      }, 500); 

    } catch (error) {
      addLog(`❌ ERROR: ${error.message}`);
      setStatus('IDLE');
      setBurnRate(0); 
    }
  };

  return (
    <div style={{ backgroundColor: '#050505', color: '#fff', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>
      <nav style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 40px', borderBottom: '1px solid #111' }}>
        <div style={{ fontSize: '20px', fontWeight: '800', letterSpacing: '-1px' }}>APERTURE <span style={{color: '#00ffaa'}}>V1</span></div>
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <div style={{ fontSize: '12px', padding: '6px 12px', border: '1px solid #00ffaa', color: '#00ffaa', borderRadius: '20px', fontWeight: 'bold' }}>● DEVNET</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', backgroundColor: '#0A0A0A', border: '1px solid #222', borderRadius: '12px', padding: '6px 12px' }}>
            {wallet && <img src={wallet.adapter.icon} alt="wallet" style={{ width: '24px', height: '24px', borderRadius: '50%' }} />}
            <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <span style={{ fontSize: '10px', color: '#666' }}>{publicKey ? `${publicKey.toBase58().slice(0, 4)}...${publicKey.toBase58().slice(-4)}` : '...'}</span>
              <span style={{ fontSize: '14px', color: '#00ffaa', fontWeight: 'bold' }}>{balance.toFixed(4)} SOL</span>
              <span style={{ fontSize: '10px', color: '#ef4444', fontWeight: 'bold' }}>⚡ {creditBalance.toFixed(6)} CRD</span>
            </div>
            <button onClick={() => setVisible(true)} style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer' }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M16 3h5v5M4 20L9 21v-5M21 3l-6 6M3 21l6-6"/></svg>
            </button>
          </div>
        </div>
      </nav>

      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '40px 20px', display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '30px' }}>
        <div>
          <h2 style={{ fontSize: '28px', marginBottom: '20px' }}>Compute Gateway</h2>
          <div style={{ backgroundColor: '#0A0A0A', borderRadius: '20px', overflow: 'hidden', border: '1px solid #111' }}>
            <div style={{ backgroundColor: '#111', padding: '10px 20px', fontSize: '12px', color: '#888', display: 'flex', justifyContent: 'space-between' }}>
              <span>payload.py</span>
              <div style={{ display: 'flex', gap: '10px' }}>
                <input type="file" ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileUpload} />
                <button onClick={() => fileInputRef.current.click()} style={{ background: 'none', border: '1px solid #333', color: '#00ffaa', fontSize: '10px', padding: '2px 8px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>UPLOAD SCRIPT</button>
              </div>
            </div>
            <textarea value={code} onChange={(e) => setCode(e.target.value)} style={{ width: '100%', height: '300px', backgroundColor: 'transparent', color: '#00ffaa', border: 'none', padding: '20px', fontFamily: 'monospace', outline: 'none', resize: 'none' }} />
          </div>

          {status === 'EXECUTING' ? (
            <button onClick={stopTask} style={{ width: '100%', marginTop: '20px', padding: '20px', borderRadius: '15px', backgroundColor: '#ff4444', color: '#fff', fontWeight: '800', border: 'none', cursor: 'pointer' }}>ABORT MISSION (STOP)</button>
          ) : (
            <button onClick={runTask} disabled={status !== 'IDLE' || !publicKey} style={{ width: '100%', marginTop: '20px', padding: '20px', borderRadius: '15px', backgroundColor: (status === 'IDLE' && publicKey) ? '#fff' : '#222', color: (status === 'IDLE' && publicKey) ? '#000' : '#555', fontWeight: '800', border: 'none', cursor: (status === 'IDLE' && publicKey) ? 'pointer' : 'not-allowed' }}>
              {status === 'IDLE' ? 'INITIATE DEPLOYMENT' : 'PROCESSING...'}
            </button>
          )}

          <div style={{ marginTop: '30px', backgroundColor: '#0A0A0A', padding: '20px', borderRadius: '15px', border: '1px solid #111' }}>
            <div style={{ fontSize: '10px', color: '#444', marginBottom: '10px' }}>SYSTEM_LOGS</div>
            {logs.map((log, i) => (
              <div key={i} style={{ fontSize: '13px', marginBottom: '5px', color: log.includes('✅') ? '#00ffaa' : (log.includes('❌') || log.includes('🛑') || log.includes('⚠️') ? '#ff4444' : '#eee'), fontFamily: 'monospace' }}>{log}</div>
            ))}
            <div ref={terminalEndRef} />
          </div>
        </div>

        <div>
          <h2 style={{ fontSize: '28px', marginBottom: '20px' }}>Network</h2>
          <div style={{ backgroundColor: '#0A0A0A', padding: '24px', borderRadius: '20px', border: '1px solid #111' }}>
            <div style={{ fontSize: '11px', color: '#444', marginBottom: '15px' }}>LOCAL_NODE_METRICS</div>
            {activeNode ? (
              <>
                <div style={{ fontSize: '24px', fontWeight: '800', color: '#00ffaa' }}>{activeNode.gpu_name}</div>
                <div style={{ marginTop: '10px', fontSize: '14px', color: '#666' }}>Node ID: <span style={{color: '#ccc'}}>{activeNode.node_id}</span></div>
                <div style={{ marginTop: '5px', fontSize: '14px', color: '#666' }}>VRAM: <span style={{color: '#ccc'}}>{activeNode.vram_total} GB</span></div>
              </>
            ) : (
              <div style={{ color: '#ff4444', fontSize: '14px' }}>📡 Searching...</div>
            )}
          </div>
          <div style={{ marginTop: '20px', backgroundColor: '#0A0A0A', padding: '24px', borderRadius: '20px', border: '1px solid #111' }}>
            <div style={{ fontSize: '11px', color: '#444', marginBottom: '10px' }}>ECONOMY</div>
            <div style={{ fontSize: '20px', fontWeight: '700' }}>{Number(burnRate || 0.0004).toFixed(4)} CRD / SEC</div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
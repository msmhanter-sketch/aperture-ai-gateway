import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000';

const ApertureCommandCenter = () => {
  // --- СОСТОЯНИЕ (STATE) ---
  const [balance, setBalance] = useState(0.1245);
  const [code, setCode] = useState(`# Aperture AI Payload\nprint("Connecting to RTX 3050...")\nimport math\nprint(f"Calculation: {math.sqrt(256)}")`);
  const [status, setStatus] = useState('IDLE'); 
  const [logs, setLogs] = useState([]);
  const [activeNode, setActiveNode] = useState(null);
  const terminalEndRef = useRef(null);

  // --- ЛОГИКА (EFFECTS) ---
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Постоянно чекаем статус нашей ноды (3050)
  useEffect(() => {
    const checkNodes = async () => {
      try {
        const res = await axios.get(`${API_URL}/active_nodes`);
        if (res.data.length > 0) setActiveNode(res.data[0]); // Берем твою 3050
      } catch (e) { console.log("Backend offline"); }
    };
    const interval = setInterval(checkNodes, 5000);
    return () => clearInterval(interval);
  }, []);

  const addLog = (msg) => {
    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  // --- ГЛАВНЫЙ ЗАПУСК (EXECUTION) ---
  const runTask = async () => {
    if (!code.trim()) return;
    setStatus('DEPLOYING');
    setLogs([]);
    addLog('🛡️ SENTINEL: Starting deep security audit...');

    try {
      const response = await axios.post(`${API_URL}/execute`, {
        code: code,
        wallet: "881Hpe3BtTquBCcm99KexH86KUgqVEvhuFeqqtkcxpkZ"
      });

      const { task_id, cost } = response.data;
      addLog(`✅ Audit passed. Cost: ${cost} USDC`);
      addLog(`📡 Dispatching to Node: ${activeNode?.node_id || 'Remote Node'}`);
      
      setStatus('EXECUTING');

      const poll = setInterval(async () => {
        const res = await axios.get(`${API_URL}/result/${task_id}`);
        if (res.data.status === 'completed') {
          clearInterval(poll);
          addLog(`🚀 NODE FINISHED.`);
          addLog(`>>> OUTPUT:\n${res.data.output}`);
          setStatus('IDLE');
        }
      }, 2000);

    } catch (error) {
      addLog(`❌ ERROR: ${error.message}`);
      setStatus('IDLE');
    }
  };

  return (
    <div style={{ backgroundColor: '#050505', color: '#fff', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>
      {/* HEADER */}
      <nav style={{ display: 'flex', justifyContent: 'space-between', padding: '20px 40px', borderBottom: '1px solid #111' }}>
        <div style={{ fontSize: '20px', fontWeight: '800', letterSpacing: '-1px' }}>APERTURE <span style={{color: '#00ffaa'}}>V1</span></div>
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <div style={{ fontSize: '14px', color: '#666' }}>Balance: <span style={{color: '#fff'}}>{balance} USDC</span></div>
          <div style={{ fontSize: '12px', padding: '6px 12px', border: '1px solid #00ffaa', color: '#00ffaa', borderRadius: '20px' }}>● DEVNET</div>
        </div>
      </nav>

      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '40px 20px', display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '30px' }}>
        
        {/* LEFT: COMPUTE ZONE */}
        <div>
          <h2 style={{ fontSize: '28px', marginBottom: '20px' }}>Compute Gateway</h2>
          
          <div style={{ backgroundColor: '#0A0A0A', borderRadius: '20px', overflow: 'hidden', border: '1px solid #111' }}>
            <div style={{ backgroundColor: '#111', padding: '10px 20px', fontSize: '12px', color: '#444' }}>payload.py</div>
            <textarea 
              value={code} onChange={(e) => setCode(e.target.value)}
              style={{ width: '100%', height: '300px', backgroundColor: 'transparent', color: '#00ffaa', border: 'none', padding: '20px', fontFamily: 'monospace', outline: 'none', resize: 'none' }}
            />
          </div>

          <button 
            onClick={runTask} disabled={status !== 'IDLE'}
            style={{ width: '100%', marginTop: '20px', padding: '20px', borderRadius: '15px', backgroundColor: status === 'IDLE' ? '#fff' : '#222', color: '#000', fontWeight: '800', border: 'none', cursor: 'pointer' }}
          >
            {status === 'IDLE' ? 'INITIATE DEPLOYMENT' : 'PROCESSING...'}
          </button>

          {/* REAL-TIME LOGS */}
          <div style={{ marginTop: '30px', backgroundColor: '#0A0A0A', padding: '20px', borderRadius: '15px', border: '1px solid #111' }}>
            <div style={{ fontSize: '10px', color: '#444', marginBottom: '10px' }}>SYSTEM_LOGS</div>
            {logs.map((log, i) => (
              <div key={i} style={{ fontSize: '13px', marginBottom: '5px', color: log.includes('✅') ? '#00ffaa' : '#eee', fontFamily: 'monospace' }}>{log}</div>
            ))}
            <div ref={terminalEndRef} />
          </div>
        </div>

        {/* RIGHT: NODE STATUS (Your 3050) */}
        <div>
          <h2 style={{ fontSize: '28px', marginBottom: '20px' }}>Network</h2>
          <div style={{ backgroundColor: '#0A0A0A', padding: '24px', borderRadius: '20px', border: '1px solid #111' }}>
            <div style={{ fontSize: '11px', color: '#444', marginBottom: '15px' }}>LOCAL_NODE_METRICS</div>
            
            {activeNode ? (
              <>
                <div style={{ fontSize: '24px', fontWeight: '800', color: '#00ffaa' }}>{activeNode.gpu_name}</div>
                <div style={{ marginTop: '10px', fontSize: '14px', color: '#666' }}>Node ID: <span style={{color: '#ccc'}}>{activeNode.node_id}</span></div>
                <div style={{ marginTop: '5px', fontSize: '14px', color: '#666' }}>VRAM: <span style={{color: '#ccc'}}>{activeNode.vram_total} GB</span></div>
                <div style={{ marginTop: '20px', padding: '10px', backgroundColor: '#00ffaa11', border: '1px solid #00ffaa33', borderRadius: '10px', color: '#00ffaa', textAlign: 'center', fontSize: '12px' }}>
                  ONLINE & READY
                </div>
              </>
            ) : (
              <div style={{ color: '#ff4444', fontSize: '14px' }}>📡 Searching for active nodes...</div>
            )}
          </div>

          <div style={{ marginTop: '20px', backgroundColor: '#0A0A0A', padding: '24px', borderRadius: '20px', border: '1px solid #111' }}>
            <div style={{ fontSize: '11px', color: '#444', marginBottom: '10px' }}>ECONOMY</div>
            <div style={{ fontSize: '20px', fontWeight: '700' }}>0.0004 SOL <span style={{ fontSize: '12px', color: '#444' }}>/ SEC</span></div>
          </div>
        </div>

      </main>
    </div>
  );
};

export default ApertureCommandCenter;
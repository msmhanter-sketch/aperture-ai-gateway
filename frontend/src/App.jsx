import React, { useState, useEffect } from 'react';
import { useWallet, useConnection } from '@solana/wallet-adapter-react';
import { WalletMultiButton, useWalletModal } from '@solana/wallet-adapter-react-ui';
import { LAMPORTS_PER_SOL } from '@solana/web3.js';
import './App.css'; 
import Dashboard from './Dashboard'; 

import logo from './assets/logo.png'; 

export default function App() {
  const { connected, publicKey, wallet } = useWallet();
  const { connection } = useConnection();
  const { setVisible } = useWalletModal();

  // Состояния
  const [showTerminal, setShowTerminal] = useState(false); // Управляет переходом в Дашборд
  const [balance, setBalance] = useState(0); 
  const [creditBalance, setCreditBalance] = useState(0.01); // 🔥 Стейт для демо-кредитов Aperture
  const [showFinanceMenu, setShowFinanceMenu] = useState(false); // Меню депозита

  // Подтягиваем баланс прямо на главную страницу
  useEffect(() => {
    if (publicKey) {
      connection.getBalance(publicKey).then((bal) => {
        setBalance(bal / LAMPORTS_PER_SOL);
      });
      // Примечание: Здесь можно добавить axios запрос к бэкенду для получения точного creditBalance из БД, 
      // но для главной страницы (лендинга) стартовое значение 0.01 выглядит отлично.
    } else {
      setBalance(0);
    }
  }, [publicKey, connection]);

  // Если юзер САМ нажал "Launch Terminal" — только тогда рендерим черный Дашборд
  if (showTerminal) {
    return <Dashboard />;
  }

  // ИНАЧЕ показываем главную светлую страницу
  return (
    <div style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      flexDirection: 'column', 
      backgroundColor: '#fafafa', 
      position: 'relative',
      overflow: 'hidden',
      fontFamily: '"Inter", sans-serif'
    }}>
      
      {/* Фоновая сетка */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        backgroundImage: 'linear-gradient(to right, #e5e7eb 1px, transparent 1px), linear-gradient(to bottom, #e5e7eb 1px, transparent 1px)',
        backgroundSize: '40px 40px', maskImage: 'radial-gradient(ellipse 60% 60% at 50% 50%, #000 20%, transparent 100%)',
        opacity: 0.5, zIndex: 0
      }}></div>
      
      {/* --- HEADER --- */}
      <header style={{ 
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
        padding: '20px 40px', borderBottom: '1px solid rgba(0,0,0,0.05)',
        background: 'rgba(255, 255, 255, 0.8)', backdropFilter: 'blur(12px)',
        position: 'relative', zIndex: 50
      }}>
        
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <img src={logo} alt="Aperture Logo" style={{ height: '56px', width: 'auto', display: 'block' }} />
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          
          {/* ЕСЛИ ПОДКЛЮЧЕН — ПОКАЗЫВАЕМ БАЛАНС И МЕНЮ, ЕСЛИ НЕТ — КНОПКУ CONNECT */}
          {connected ? (
            <div style={{ position: 'relative' }}>
              <div 
                onClick={() => setShowFinanceMenu(!showFinanceMenu)}
                style={{ 
                  display: 'flex', alignItems: 'center', gap: '10px', 
                  backgroundColor: '#ffffff', border: '1px solid #e5e7eb', 
                  borderRadius: '12px', padding: '6px 12px', cursor: 'pointer',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.02)', transition: 'all 0.2s'
                }}
                onMouseOver={(e) => e.currentTarget.style.borderColor = '#d1d5db'}
                onMouseOut={(e) => e.currentTarget.style.borderColor = '#e5e7eb'}
              >
                {wallet && <img src={wallet.adapter.icon} alt="wallet" style={{ width: '20px', height: '20px', borderRadius: '50%' }} />}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '10px', color: '#6b7280', fontWeight: '600', lineHeight: '1' }}>
                    {publicKey ? `${publicKey.toBase58().slice(0, 4)}...${publicKey.toBase58().slice(-4)}` : ''}
                  </span>
                  
                  {/* Основной баланс SOL */}
                  <span style={{ fontSize: '14px', color: '#111827', fontWeight: '800', lineHeight: '1.2' }}>
                    {balance.toFixed(4)} SOL
                  </span>

                  {/* 🔥 НОВЫЙ БЛОК: Сгорающий баланс Кредитов */}
                  <span style={{ 
                    fontSize: '10px', 
                    color: '#64748b', 
                    fontFamily: 'monospace', 
                    marginTop: '2px',
                    borderTop: '1px solid #e5e7eb',
                    paddingTop: '2px'
                  }}>
                    <span style={{ color: '#ef4444' }}>⚡</span> DEMO: {creditBalance.toFixed(4)} CRD
                  </span>

                </div>
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6b7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: showFinanceMenu ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </div>

              {/* Выпадающее светлое меню */}
              {showFinanceMenu && (
                <div style={{ 
                  position: 'absolute', top: '100%', right: 0, marginTop: '10px',
                  width: '260px', backgroundColor: '#ffffff', border: '1px solid #e5e7eb', 
                  borderRadius: '16px', padding: '20px', boxShadow: '0 10px 25px rgba(0,0,0,0.05)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                    <span style={{ fontSize: '12px', color: '#6b7280', fontWeight: '700' }}>WALLET BALANCE</span>
                    <button onClick={() => setShowFinanceMenu(false)} style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer' }}>✕</button>
                  </div>
                  
                  <div style={{ fontSize: '28px', fontWeight: '900', color: '#111827', marginBottom: '4px' }}>
                    {balance.toFixed(4)} <span style={{ fontSize: '16px', color: '#10b981' }}>SOL</span>
                  </div>

                  {/* 🔥 НОВЫЙ БЛОК В МЕНЮ: Кредиты */}
                  <div style={{ fontSize: '14px', fontWeight: '600', color: '#64748b', marginBottom: '20px', fontFamily: 'monospace' }}>
                    <span style={{ color: '#ef4444' }}>⚡</span> {creditBalance.toFixed(4)} APERTURE CREDITS
                  </div>

                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button style={{ flex: 1, padding: '10px 0', backgroundColor: '#111827', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: '700', cursor: 'pointer' }}>
                      DEPOSIT
                    </button>
                    <button style={{ flex: 1, padding: '10px 0', backgroundColor: '#f3f4f6', color: '#111827', border: '1px solid #e5e7eb', borderRadius: '8px', fontWeight: '700', cursor: 'pointer' }}>
                      WITHDRAW
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.05))' }}>
              <WalletMultiButton />
            </div>
          )}
          
          {/* Кнопка смены кошелька (остается всегда) */}
          <button 
            onClick={() => setVisible(true)}
            style={{ 
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: '42px', height: '42px', borderRadius: '12px', 
              backgroundColor: '#ffffff', border: '1px solid #e5e7eb', cursor: 'pointer',
              boxShadow: '0 2px 10px rgba(0,0,0,0.02)', transition: 'all 0.2s ease'
            }}
            title="Сменить кошелек"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#111827" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M16 3h5v5M4 20L9 21v-5M21 3l-6 6M3 21l6-6"/>
            </svg>
          </button>
        </div>
      </header>

      {/* --- MAIN CONTENT AREA --- */}
      <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', padding: '0 40px', zIndex: 10 }}>
        
        <div className="hidden lg:block" style={{ position: 'absolute', left: '40px', width: '280px', background: 'rgba(255, 255, 255, 0.6)', backdropFilter: 'blur(16px)', border: '1px solid rgba(0,0,0,0.05)', borderRadius: '16px', padding: '24px', boxShadow: '0 10px 30px rgba(0,0,0,0.03)' }}>
          <div style={{ fontSize: '10px', fontWeight: '700', letterSpacing: '1px', color: '#9ca3af', marginBottom: '20px' }}>// NETWORK_TELEMETRY</div>
          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Active GPU Nodes</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '20px', fontWeight: '800', color: '#111827' }}>0 <span style={{ fontSize: '10px', fontWeight: '700', padding: '2px 8px', borderRadius: '999px', background: '#fee2e2', color: '#ef4444', border: '1px solid #fecaca' }}>OFFLINE</span></div>
          </div>
          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Avg. Latency</div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: '#d1d5db' }}>---</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Total Compute (TFLOPS)</div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: '#d1d5db' }}>0.0</div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', maxWidth: '600px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '6px 16px', borderRadius: '999px', background: '#ffffff', border: '1px solid #e5e7eb', boxShadow: '0 2px 8px rgba(0,0,0,0.02)', fontSize: '11px', fontWeight: '700', letterSpacing: '1px', color: '#374151', marginBottom: '32px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981', display: 'inline-block' }}></span> SOLANA DEVNET
          </div>

          <h1 style={{ fontSize: 'clamp(48px, 8vw, 84px)', fontWeight: '900', letterSpacing: '-0.04em', color: '#111827', margin: '0 0 16px 0', lineHeight: '1' }}>APERTURE</h1>
          <p style={{ fontSize: '18px', color: '#6b7280', lineHeight: '1.6', fontWeight: '400', marginBottom: '40px', maxWidth: '400px' }}>Autonomous AI Compute Protocol.<br/>Real-time validation settled in Lamports.</p>

          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap' }}>
            
            {/* ЕСЛИ ПОДКЛЮЧЕН КОШЕЛЕК — ПОКАЗЫВАЕМ КНОПКУ ПЕРЕХОДА В ДАШБОРД */}
            {connected ? (
              <button 
                onClick={() => setShowTerminal(true)}
                style={{ height: '48px', padding: '0 32px', backgroundColor: '#512da8', color: '#fff', borderRadius: '4px', border: 'none', fontSize: '15px', fontWeight: '700', cursor: 'pointer', boxShadow: '0 4px 15px rgba(81, 45, 168, 0.4)' }}
              >
                Launch Terminal
              </button>
            ) : (
              <div style={{ filter: 'drop-shadow(0 10px 15px rgba(0,0,0,0.1))' }}>
                <WalletMultiButton />
              </div>
            )}

            <button style={{ display: 'flex', alignItems: 'center', gap: '8px', height: '48px', padding: '0 24px', backgroundColor: '#111827', color: '#ffffff', borderRadius: '4px', border: 'none', fontSize: '15px', fontWeight: '600', cursor: 'pointer', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
              Provide Compute
            </button>
          </div>
        </div>

        <div className="hidden lg:block" style={{ position: 'absolute', right: '40px', width: '280px', background: 'rgba(255, 255, 255, 0.6)', backdropFilter: 'blur(16px)', border: '1px solid rgba(0,0,0,0.05)', borderRadius: '16px', padding: '24px', boxShadow: '0 10px 30px rgba(0,0,0,0.03)' }}>
          <div style={{ fontSize: '10px', fontWeight: '700', letterSpacing: '1px', color: '#9ca3af', marginBottom: '20px' }}>// SENTINEL_STATE</div>
          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>AI Auditor Status</div>
            <div style={{ fontSize: '16px', fontWeight: '800', color: '#f59e0b', letterSpacing: '0.5px' }}>STANDBY</div>
          </div>
          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Payloads Analyzed</div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: '#111827' }}>0</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Burn Rate (SOL/sec)</div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: '#d1d5db', fontFamily: 'monospace' }}>0.00000</div>
          </div>
        </div>

      </main>

      <footer style={{ padding: '24px', textAlign: 'center', position: 'relative', zIndex: 20, fontSize: '11px', fontWeight: '600', letterSpacing: '2px', color: '#9ca3af' }}>
        APERTURE PROTOCOL V1.0 <span style={{ margin: '0 8px', color: '#d1d5db' }}>|</span> ZERO_REQUIEM
      </footer>

    </div>
  );
}
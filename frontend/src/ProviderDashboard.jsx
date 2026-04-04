import React, { useState } from 'react';

const ProviderDashboard = () => {
  const [isOnline, setIsOnline] = useState(false);
  const [earnings, setEarnings] = useState(0.00);

  return (
    <div className="dashboard-container">
      <header className="dash-header">
        <h1>Node Management Console</h1>
        <button 
          className={`status-btn ${isOnline ? 'online' : 'offline'}`}
          onClick={() => setIsOnline(!isOnline)}
        >
          {isOnline ? '● NODE ONLINE' : '○ GO LIVE'}
        </button>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Earnings</h3>
          <p className="stat-value">{earnings} USDC</p>
        </div>
        <div className="stat-card">
          <h3>Active Tasks</h3>
          <p className="stat-value">0</p>
        </div>
        <div className="stat-card">
          <h3>Hardware Load</h3>
          <p className="stat-value">{isOnline ? '12%' : '0%'}</p>
        </div>
      </div>

      <section className="node-settings">
        <h2>Hardware Specs</h2>
        <div className="spec-row">
          <span>CPU:</span> <span>12 Cores (Virtualized)</span>
        </div>
        <div className="spec-row">
          <span>RAM:</span> <span>32GB DDR5</span>
        </div>
        <div className="spec-row">
          <span>Price/Sec:</span> <span>0.0005 SOL</span>
        </div>
      </section>
    </div>
  );
};

export default ProviderDashboard;
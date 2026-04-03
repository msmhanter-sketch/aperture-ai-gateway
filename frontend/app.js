const API_URL = 'http://127.0.0.1:8000';

let userWalletAddress = null;
let guestId = localStorage.getItem('aperture_guest_id');

if (!guestId) {
    guestId = 'guest_' + Math.random().toString(36).substring(2, 10);
    localStorage.setItem('aperture_guest_id', guestId);
}

const connection = new solanaWeb3.Connection(solanaWeb3.clusterApiUrl('devnet'), 'confirmed');

const balanceDisplay = document.getElementById('balance-display');
const demoBadge = document.getElementById('demo-badge');
const codeInput = document.getElementById('code-input');
const executeBtn = document.getElementById('execute-btn');
const terminal = document.getElementById('terminal-output');
const connectWalletBtn = document.getElementById('connect-wallet-btn');

// Элементы модалки
const walletModal = document.getElementById('wallet-modal');
const closeModalBtn = document.getElementById('close-modal-btn');
const walletList = document.getElementById('wallet-list');

function logToTerminal(message, type = 'info') {
    const div = document.createElement('div');
    div.className = `log ${type}`;
    div.innerText = `> ${message}`;
    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;
}

async function fetchBalance() {
    try {
        const url = userWalletAddress 
            ? `${API_URL}/balance?wallet=${userWalletAddress}` 
            : `${API_URL}/balance?guest_id=${guestId}`;

        const response = await fetch(url);
        const data = await response.json();
        balanceDisplay.innerText = data.balance.toFixed(4);
        
        if (data.is_demo && !userWalletAddress) {
            demoBadge.classList.remove('hidden');
        } else {
            demoBadge.classList.add('hidden');
        }
    } catch (error) {
        logToTerminal('Connection to Gateway failed.', 'error');
    }
}

async function syncWalletWithBackend(walletAddress) {
    try {
        logToTerminal("Syncing identity with Aperture Gateway...", "system");
        const response = await fetch(`${API_URL}/balance?wallet=${walletAddress}&guest_id=${guestId}`);
        const data = await response.json();
        
        balanceDisplay.innerText = data.balance.toFixed(4);
        demoBadge.classList.add('hidden');
        logToTerminal("Gateway sync complete. You are now using Web3 Identity.", "success");
    } catch (error) {
        logToTerminal('Backend sync failed.', 'error');
    }
}

// --- ЛОГИКА УНИВЕРСАЛЬНОГО АДАПТЕРА ---
const SUPPORTED_WALLETS = [
    { name: 'Phantom', getProvider: () => window.phantom?.solana || window.solana },
    { name: 'Solflare', getProvider: () => window.solflare },
    { name: 'Backpack', getProvider: () => window.backpack }
];

// Открываем модалку по кнопке "Connect Wallet"
connectWalletBtn.addEventListener('click', () => {
    walletList.innerHTML = ''; // Чистим старые кнопки
    let foundWallets = 0;

    SUPPORTED_WALLETS.forEach(wallet => {
        const provider = wallet.getProvider();
        if (provider) {
            foundWallets++;
            const btn = document.createElement('button');
            btn.className = 'wallet-option-btn';
            btn.innerText = wallet.name;
            btn.onclick = () => connectSpecificWallet(provider, wallet.name);
            walletList.appendChild(btn);
        }
    });

    if (foundWallets === 0) {
        walletList.innerHTML = '<p style="color: var(--danger); font-size: 14px;">No Solana wallets detected. Install Phantom, Solflare, or Backpack.</p>';
    }

    walletModal.classList.remove('hidden');
});

// Закрываем модалку
closeModalBtn.addEventListener('click', () => {
    walletModal.classList.add('hidden');
});

// Функция подключения конкретного провайдера
async function connectSpecificWallet(provider, walletName) {
    try {
        walletModal.classList.add('hidden'); // прячем модалку
        logToTerminal(`Requesting secure connection to ${walletName}...`, "system");
        
        const resp = await provider.connect();
        userWalletAddress = resp.publicKey.toString();
        
        logToTerminal(`${walletName} connected: ${userWalletAddress.slice(0, 4)}...${userWalletAddress.slice(-4)}`, "success");
        
        connectWalletBtn.innerText = `${userWalletAddress.slice(0, 4)}...${userWalletAddress.slice(-4)}`;
        connectWalletBtn.classList.remove('outline');
        connectWalletBtn.classList.add('primary');
        
        const devnetBalance = await connection.getBalance(resp.publicKey);
        const solBalance = devnetBalance / solanaWeb3.LAMPORTS_PER_SOL;
        logToTerminal(`Devnet SOL Balance: ${solBalance} SOL`, "info");

        await syncWalletWithBackend(userWalletAddress);
    } catch (err) {
        logToTerminal(`Connection rejected or failed: ${err.message}`, "error");
    }
}

// Отправка кода
executeBtn.addEventListener('click', async () => {
    const code = codeInput.value.trim();
    if (!code) {
        logToTerminal('Payload is empty.', 'error');
        return;
    }

    executeBtn.disabled = true;
    executeBtn.innerText = 'Analyzing...';
    logToTerminal('Sending payload to AI-Auditor...', 'system');

    try {
        const response = await fetch(`${API_URL}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                code: code, 
                guest_id: userWalletAddress ? null : guestId,
                wallet: userWalletAddress 
            })
        });

        const result = await response.json();

        if (response.ok) {
            logToTerminal(`AI Analysis complete. CPU: ${result.ai_analysis.cpu}, RAM: ${result.ai_analysis.ram}`, 'info');
            logToTerminal(`Reason: ${result.ai_analysis.reason}`, 'info');
            logToTerminal(`Cost: ${result.cost} USDC. Execution Approved.`, 'success');
            balanceDisplay.innerText = result.new_balance.toFixed(4);
        } else {
            logToTerminal(`Gateway Error: ${result.detail}`, 'error');
        }
    } catch (error) {
        logToTerminal(`Network error: ${error.message}`, 'error');
    } finally {
        executeBtn.disabled = false;
        executeBtn.innerText = 'Deploy & Execute';
    }
});

logToTerminal(`Session started. Guest ID: ${guestId}`, 'system');
fetchBalance();
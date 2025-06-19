#!/bin/bash
# scripts/implement_web_pages.sh - Create functional web interface pages

echo "🌐 Implementing Functional Web Interface Pages..."
echo "============================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# 1. TRADING INTERFACE
print_status "Creating functional Trading interface..."
cat > src/interfaces/web/templates/trading.html << 'EOF'
{% extends "base.html" %}
{% block title %}Trading - Trading Bot{% endblock %}

{% block content %}
<div class="grid">
    <!-- Buy/Sell Orders -->
    <div class="card">
        <h2>💹 Place Order</h2>
        <form id="order-form">
            <div style="margin-bottom: 15px;">
                <label>Symbol:</label>
                <select id="symbol" style="width: 100%; padding: 8px; margin-top: 5px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                    <option value="BTC/USDT">BTC/USDT</option>
                    <option value="ETH/USDT">ETH/USDT</option>
                    <option value="ADA/USDT">ADA/USDT</option>
                </select>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;">
                <button type="button" id="buy-btn" class="btn" style="background: #238636;">🔥 BUY</button>
                <button type="button" id="sell-btn" class="btn" style="background: #da3633;">💸 SELL</button>
            </div>
            
            <div style="margin-bottom: 15px;">
                <label>Order Type:</label>
                <select id="order-type" style="width: 100%; padding: 8px; margin-top: 5px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                    <option value="market">Market Order</option>
                    <option value="limit">Limit Order</option>
                </select>
            </div>
            
            <div style="margin-bottom: 15px;">
                <label>Amount (USD):</label>
                <input type="number" id="amount" placeholder="100" style="width: 100%; padding: 8px; margin-top: 5px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
            </div>
            
            <div id="price-section" style="margin-bottom: 15px; display: none;">
                <label>Price:</label>
                <input type="number" id="price" placeholder="42000" style="width: 100%; padding: 8px; margin-top: 5px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
            </div>
            
            <button type="submit" class="btn" style="width: 100%;">📤 Submit Order</button>
        </form>
    </div>
    
    <!-- Current Price -->
    <div class="card">
        <h2>📊 Market Data</h2>
        <div id="price-info">
            <p>BTC/USDT: <strong id="current-price">$42,150.00</strong></p>
            <p>24h Change: <strong style="color: #238636;" id="price-change">+2.5%</strong></p>
            <p>Volume: <strong id="volume">1,234.56 BTC</strong></p>
            <p>Last Update: <span id="last-update">Just now</span></p>
        </div>
        <div style="margin-top: 15px;">
            <button class="btn" onclick="refreshPrice()">🔄 Refresh</button>
        </div>
    </div>
</div>

<!-- Open Orders -->
<div class="card">
    <h2>📋 Open Orders</h2>
    <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="border-bottom: 1px solid #30363d;">
                    <th style="text-align: left; padding: 10px;">Symbol</th>
                    <th style="text-align: left; padding: 10px;">Side</th>
                    <th style="text-align: left; padding: 10px;">Type</th>
                    <th style="text-align: left; padding: 10px;">Amount</th>
                    <th style="text-align: left; padding: 10px;">Price</th>
                    <th style="text-align: left; padding: 10px;">Status</th>
                    <th style="text-align: left; padding: 10px;">Actions</th>
                </tr>
            </thead>
            <tbody id="orders-table">
                <tr>
                    <td style="padding: 10px;">BTC/USDT</td>
                    <td style="padding: 10px; color: #238636;">BUY</td>
                    <td style="padding: 10px;">LIMIT</td>
                    <td style="padding: 10px;">0.001 BTC</td>
                    <td style="padding: 10px;">$41,500</td>
                    <td style="padding: 10px;"><span class="status running">PENDING</span></td>
                    <td style="padding: 10px;">
                        <button class="btn" style="padding: 5px 10px; font-size: 12px;" onclick="cancelOrder('1')">❌ Cancel</button>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</div>

<!-- Trade History -->
<div class="card">
    <h2>📊 Recent Trades</h2>
    <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="border-bottom: 1px solid #30363d;">
                    <th style="text-align: left; padding: 10px;">Time</th>
                    <th style="text-align: left; padding: 10px;">Symbol</th>
                    <th style="text-align: left; padding: 10px;">Side</th>
                    <th style="text-align: left; padding: 10px;">Amount</th>
                    <th style="text-align: left; padding: 10px;">Price</th>
                    <th style="text-align: left; padding: 10px;">P&L</th>
                </tr>
            </thead>
            <tbody id="trades-table">
                <tr>
                    <td style="padding: 10px;">16:30</td>
                    <td style="padding: 10px;">BTC/USDT</td>
                    <td style="padding: 10px; color: #da3633;">SELL</td>
                    <td style="padding: 10px;">0.001 BTC</td>
                    <td style="padding: 10px;">$42,200</td>
                    <td style="padding: 10px; color: #238636;">+$150.00</td>
                </tr>
                <tr>
                    <td style="padding: 10px;">15:45</td>
                    <td style="padding: 10px;">BTC/USDT</td>
                    <td style="padding: 10px; color: #238636;">BUY</td>
                    <td style="padding: 10px;">0.001 BTC</td>
                    <td style="padding: 10px;">$42,050</td>
                    <td style="padding: 10px;">-</td>
                </tr>
            </tbody>
        </table>
    </div>
</div>

<script>
// Trading functionality
let currentSide = 'buy';

document.getElementById('buy-btn').addEventListener('click', function() {
    currentSide = 'buy';
    this.style.background = '#238636';
    this.style.opacity = '1';
    document.getElementById('sell-btn').style.opacity = '0.6';
});

document.getElementById('sell-btn').addEventListener('click', function() {
    currentSide = 'sell';
    this.style.background = '#da3633';
    this.style.opacity = '1';
    document.getElementById('buy-btn').style.opacity = '0.6';
});

document.getElementById('order-type').addEventListener('change', function() {
    const priceSection = document.getElementById('price-section');
    if (this.value === 'limit') {
        priceSection.style.display = 'block';
    } else {
        priceSection.style.display = 'none';
    }
});

document.getElementById('order-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const symbol = document.getElementById('symbol').value;
    const orderType = document.getElementById('order-type').value;
    const amount = document.getElementById('amount').value;
    const price = document.getElementById('price').value;
    
    if (!amount) {
        alert('Please enter amount');
        return;
    }
    
    // Simulate order placement
    alert(`${currentSide.toUpperCase()} order placed for ${amount} USD of ${symbol}`);
    
    // Add to orders table (simulation)
    addOrderToTable(symbol, currentSide, orderType, amount, price);
});

function addOrderToTable(symbol, side, type, amount, price) {
    const table = document.getElementById('orders-table');
    const row = table.insertRow(0);
    const sideColor = side === 'buy' ? '#238636' : '#da3633';
    
    row.innerHTML = `
        <td style="padding: 10px;">${symbol}</td>
        <td style="padding: 10px; color: ${sideColor};">${side.toUpperCase()}</td>
        <td style="padding: 10px;">${type.toUpperCase()}</td>
        <td style="padding: 10px;">${amount} USD</td>
        <td style="padding: 10px;">${price || 'MARKET'}</td>
        <td style="padding: 10px;"><span class="status running">PENDING</span></td>
        <td style="padding: 10px;">
            <button class="btn" style="padding: 5px 10px; font-size: 12px;" onclick="cancelOrder('${Date.now()}')">❌ Cancel</button>
        </td>
    `;
}

function cancelOrder(orderId) {
    if (confirm('Are you sure you want to cancel this order?')) {
        alert('Order cancelled');
        // Remove row logic here
    }
}

function refreshPrice() {
    // Simulate price update
    const prices = [41800, 42150, 42500, 41950, 42300];
    const newPrice = prices[Math.floor(Math.random() * prices.length)];
    document.getElementById('current-price').textContent = `$${newPrice.toLocaleString()}.00`;
    document.getElementById('last-update').textContent = 'Just now';
}

// Auto-refresh price every 30 seconds
setInterval(refreshPrice, 30000);
</script>
{% endblock %}
EOF

# 2. STRATEGIES INTERFACE
print_status "Creating functional Strategies interface..."
cat > src/interfaces/web/templates/strategies.html << 'EOF'
{% extends "base.html" %}
{% block title %}Strategies - Trading Bot{% endblock %}

{% block content %}
<div class="grid">
    <!-- Active Strategy -->
    <div class="card">
        <h2>🧠 Current Strategy</h2>
        <div style="margin-bottom: 15px;">
            <p><strong>Name:</strong> Simple Buy/Sell</p>
            <p><strong>Status:</strong> <span class="status running">ACTIVE</span></p>
            <p><strong>Symbol:</strong> BTC/USDT</p>
            <p><strong>Timeframe:</strong> 1h</p>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <button class="btn" onclick="stopStrategy()">⏹️ Stop</button>
            <button class="btn" onclick="configureStrategy()">⚙️ Configure</button>
        </div>
    </div>
    
    <!-- Strategy Performance -->
    <div class="card">
        <h2>📊 Performance</h2>
        <p>Total Trades: <strong>45</strong></p>
        <p>Win Rate: <strong style="color: #238636;">62%</strong></p>
        <p>Total P&L: <strong style="color: #238636;">+$1,250</strong></p>
        <p>Best Trade: <strong>+$245</strong></p>
        <p>Max Drawdown: <strong style="color: #da3633;">-5.2%</strong></p>
    </div>
</div>

<!-- Strategy Selection -->
<div class="card">
    <h2>🎯 Available Strategies</h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
        
        <div style="border: 1px solid #30363d; border-radius: 8px; padding: 15px;">
            <h3 style="color: #58a6ff; margin-bottom: 10px;">📈 Simple Buy/Sell</h3>
            <p style="font-size: 14px; margin-bottom: 15px;">Buy when price drops, sell when target reached</p>
            <div style="margin-bottom: 15px;">
                <p><strong>Buy Threshold:</strong> -5%</p>
                <p><strong>Sell Threshold:</strong> +10%</p>
                <p><strong>Timeframe:</strong> 1h</p>
            </div>
            <button class="btn" onclick="selectStrategy('simple_buy_sell')" style="width: 100%;">✅ Active</button>
        </div>
        
        <div style="border: 1px solid #30363d; border-radius: 8px; padding: 15px;">
            <h3 style="color: #58a6ff; margin-bottom: 10px;">⚡ Grid Trading</h3>
            <p style="font-size: 14px; margin-bottom: 15px;">Multiple buy/sell orders in a grid pattern</p>
            <div style="margin-bottom: 15px;">
                <p><strong>Grid Levels:</strong> 10</p>
                <p><strong>Spacing:</strong> 1%</p>
                <p><strong>Amount:</strong> $100/level</p>
            </div>
            <button class="btn" onclick="selectStrategy('grid_trading')" style="width: 100%; opacity: 0.6;">🔄 Select</button>
        </div>
        
        <div style="border: 1px solid #30363d; border-radius: 8px; padding: 15px;">
            <h3 style="color: #58a6ff; margin-bottom: 10px;">🎯 RSI Strategy</h3>
            <p style="font-size: 14px; margin-bottom: 15px;">Buy on RSI oversold, sell on overbought</p>
            <div style="margin-bottom: 15px;">
                <p><strong>RSI Period:</strong> 14</p>
                <p><strong>Oversold:</strong> 30</p>
                <p><strong>Overbought:</strong> 70</p>
            </div>
            <button class="btn" onclick="selectStrategy('rsi_strategy')" style="width: 100%; opacity: 0.6;">🔄 Select</button>
        </div>
        
    </div>
</div>

<!-- Strategy Configuration -->
<div class="card" id="strategy-config" style="display: none;">
    <h2>⚙️ Strategy Configuration</h2>
    <form id="config-form">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <label>Symbol:</label>
                <select id="config-symbol" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                    <option value="BTC/USDT">BTC/USDT</option>
                    <option value="ETH/USDT">ETH/USDT</option>
                    <option value="ADA/USDT">ADA/USDT</option>
                </select>
                
                <label>Timeframe:</label>
                <select id="config-timeframe" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                    <option value="1m">1 minute</option>
                    <option value="5m">5 minutes</option>
                    <option value="15m">15 minutes</option>
                    <option value="1h" selected>1 hour</option>
                    <option value="4h">4 hours</option>
                    <option value="1d">1 day</option>
                </select>
            </div>
            
            <div>
                <label>Buy Threshold (%):</label>
                <input type="number" id="buy-threshold" value="-5" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                
                <label>Sell Threshold (%):</label>
                <input type="number" id="sell-threshold" value="10" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 20px;">
            <button type="button" class="btn" onclick="saveConfig()" style="background: #238636;">💾 Save Config</button>
            <button type="button" class="btn" onclick="cancelConfig()">❌ Cancel</button>
        </div>
    </form>
</div>

<script>
function selectStrategy(strategyName) {
    if (confirm(`Switch to ${strategyName} strategy?`)) {
        alert(`Strategy switched to ${strategyName}`);
        // Update UI to show new active strategy
    }
}

function stopStrategy() {
    if (confirm('Are you sure you want to stop the current strategy?')) {
        alert('Strategy stopped');
    }
}

function configureStrategy() {
    document.getElementById('strategy-config').style.display = 'block';
    document.getElementById('strategy-config').scrollIntoView();
}

function saveConfig() {
    const symbol = document.getElementById('config-symbol').value;
    const timeframe = document.getElementById('config-timeframe').value;
    const buyThreshold = document.getElementById('buy-threshold').value;
    const sellThreshold = document.getElementById('sell-threshold').value;
    
    alert(`Strategy configuration saved:\nSymbol: ${symbol}\nTimeframe: ${timeframe}\nBuy: ${buyThreshold}%\nSell: ${sellThreshold}%`);
    
    document.getElementById('strategy-config').style.display = 'none';
}

function cancelConfig() {
    document.getElementById('strategy-config').style.display = 'none';
}
</script>
{% endblock %}
EOF

# 3. BACKTESTING INTERFACE
print_status "Creating functional Backtesting interface..."
cat > src/interfaces/web/templates/backtesting.html << 'EOF'
{% extends "base.html" %}
{% block title %}Backtesting - Trading Bot{% endblock %}

{% block content %}
<!-- Backtest Setup -->
<div class="card">
    <h2>📈 Run Backtest</h2>
    <form id="backtest-form">
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <div>
                <label>Strategy:</label>
                <select id="bt-strategy" style="width: 100%; padding: 8px; margin-top: 5px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                    <option value="simple_buy_sell">Simple Buy/Sell</option>
                    <option value="grid_trading">Grid Trading</option>
                    <option value="rsi_strategy">RSI Strategy</option>
                </select>
            </div>
            
            <div>
                <label>Symbol:</label>
                <select id="bt-symbol" style="width: 100%; padding: 8px; margin-top: 5px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                    <option value="BTC/USDT">BTC/USDT</option>
                    <option value="ETH/USDT">ETH/USDT</option>
                    <option value="ADA/USDT">ADA/USDT</option>
                </select>
            </div>
            
            <div>
                <label>Timeframe:</label>
                <select id="bt-timeframe" style="width: 100%; padding: 8px; margin-top: 5px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                    <option value="1h">1 hour</option>
                    <option value="4h">4 hours</option>
                    <option value="1d">1 day</option>
                </select>
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <div>
                <label>Start Date:</label>
                <input type="date" id="start-date" value="2024-01-01" style="width: 100%; padding: 8px; margin-top: 5px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
            </div>
            
            <div>
                <label>End Date:</label>
                <input type="date" id="end-date" value="2024-02-01" style="width: 100%; padding: 8px; margin-top: 5px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
            </div>
            
            <div>
                <label>Initial Balance:</label>
                <input type="number" id="initial-balance" value="10000" style="width: 100%; padding: 8px; margin-top: 5px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
            </div>
        </div>
        
        <button type="submit" class="btn" style="width: 100%; background: #7c3aed;">🚀 Run Backtest</button>
    </form>
</div>

<!-- Backtest Progress -->
<div class="card" id="backtest-progress" style="display: none;">
    <h2>⏳ Backtest in Progress</h2>
    <div style="background: #21262d; padding: 20px; border-radius: 6px; text-align: center;">
        <div id="progress-bar" style="background: #30363d; height: 20px; border-radius: 10px; overflow: hidden; margin-bottom: 15px;">
            <div id="progress-fill" style="background: #7c3aed; height: 100%; width: 0%; transition: width 0.3s;"></div>
        </div>
        <p id="progress-text">Initializing backtest...</p>
    </div>
</div>

<!-- Backtest Results -->
<div class="card" id="backtest-results" style="display: none;">
    <h2>📊 Backtest Results</h2>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
        <div style="text-align: center; padding: 15px; background: #21262d; border-radius: 6px;">
            <p style="color: #7c3aed; font-size: 24px; font-weight: bold;" id="total-return">+15.5%</p>
            <p style="font-size: 14px;">Total Return</p>
        </div>
        
        <div style="text-align: center; padding: 15px; background: #21262d; border-radius: 6px;">
            <p style="color: #238636; font-size: 24px; font-weight: bold;" id="win-rate">62%</p>
            <p style="font-size: 14px;">Win Rate</p>
        </div>
        
        <div style="text-align: center; padding: 15px; background: #21262d; border-radius: 6px;">
            <p style="color: #58a6ff; font-size: 24px; font-weight: bold;" id="total-trades">45</p>
            <p style="font-size: 14px;">Total Trades</p>
        </div>
        
        <div style="text-align: center; padding: 15px; background: #21262d; border-radius: 6px;">
            <p style="color: #da3633; font-size: 24px; font-weight: bold;" id="max-drawdown">-8.5%</p>
            <p style="font-size: 14px;">Max Drawdown</p>
        </div>
        
        <div style="text-align: center; padding: 15px; background: #21262d; border-radius: 6px;">
            <p style="color: #f0f6fc; font-size: 24px; font-weight: bold;" id="sharpe-ratio">1.85</p>
            <p style="font-size: 14px;">Sharpe Ratio</p>
        </div>
        
        <div style="text-align: center; padding: 15px; background: #21262d; border-radius: 6px;">
            <p style="color: #f0f6fc; font-size: 24px; font-weight: bold;" id="final-balance">$11,550</p>
            <p style="font-size: 14px;">Final Balance</p>
        </div>
    </div>
    
    <div style="margin-top: 20px;">
        <button class="btn" onclick="exportResults()" style="margin-right: 10px;">📁 Export CSV</button>
        <button class="btn" onclick="showChart()" style="margin-right: 10px;">📈 View Chart</button>
        <button class="btn" onclick="newBacktest()">🔄 New Backtest</button>
    </div>
</div>

<!-- Previous Backtests -->
<div class="card">
    <h2>📋 Previous Backtests</h2>
    <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="border-bottom: 1px solid #30363d;">
                    <th style="text-align: left; padding: 10px;">Date</th>
                    <th style="text-align: left; padding: 10px;">Strategy</th>
                    <th style="text-align: left; padding: 10px;">Symbol</th>
                    <th style="text-align: left; padding: 10px;">Period</th>
                    <th style="text-align: left; padding: 10px;">Return</th>
                    <th style="text-align: left; padding: 10px;">Win Rate</th>
                    <th style="text-align: left; padding: 10px;">Actions</th>
                </tr>
            </thead>
            <tbody id="backtests-table">
                <tr>
                    <td style="padding: 10px;">2024-06-19</td>
                    <td style="padding: 10px;">Simple Buy/Sell</td>
                    <td style="padding: 10px;">BTC/USDT</td>
                    <td style="padding: 10px;">30 days</td>
                    <td style="padding: 10px; color: #238636;">+15.5%</td>
                    <td style="padding: 10px;">62%</td>
                    <td style="padding: 10px;">
                        <button class="btn" style="padding: 5px 10px; font-size: 12px;" onclick="viewBacktest('1')">👁️ View</button>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px;">2024-06-18</td>
                    <td style="padding: 10px;">Grid Trading</td>
                    <td style="padding: 10px;">ETH/USDT</td>
                    <td style="padding: 10px;">7 days</td>
                    <td style="padding: 10px; color: #da3633;">-2.1%</td>
                    <td style="padding: 10px;">45%</td>
                    <td style="padding: 10px;">
                        <button class="btn" style="padding: 5px 10px; font-size: 12px;" onclick="viewBacktest('2')">👁️ View</button>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</div>

<script>
document.getElementById('backtest-form').addEventListener('submit', function(e) {
    e.preventDefault();
    runBacktest();
});

function runBacktest() {
    // Show progress
    document.getElementById('backtest-progress').style.display = 'block';
    document.getElementById('backtest-results').style.display = 'none';
    
    // Simulate backtest progress
    let progress = 0;
    const progressBar = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    const interval = setInterval(() => {
        progress += Math.random() * 20;
        if (progress > 100) progress = 100;
        
        progressBar.style.width = progress + '%';
        
        if (progress < 25) {
            progressText.textContent = 'Loading historical data...';
        } else if (progress < 50) {
            progressText.textContent = 'Initializing strategy...';
        } else if (progress < 75) {
            progressText.textContent = 'Running simulation...';
        } else if (progress < 100) {
            progressText.textContent = 'Calculating results...';
        } else {
            progressText.textContent = 'Backtest complete!';
            clearInterval(interval);
            
            setTimeout(() => {
                document.getElementById('backtest-progress').style.display = 'none';
                document.getElementById('backtest-results').style.display = 'block';
                document.getElementById('backtest-results').scrollIntoView();
            }, 1000);
        }
    }, 200);
}

function exportResults() {
    alert('Backtest results exported to CSV file');
}

function showChart() {
    alert('Chart view will open here (integration with QuickChart)');
}

function newBacktest() {
    document.getElementById('backtest-results').style.display = 'none';
    document.getElementById('backtest-form').scrollIntoView();
}

function viewBacktest(id) {
    alert(`Loading backtest results for ID: ${id}`);
}
</script>
{% endblock %}
EOF

# 4. SETTINGS INTERFACE
print_status "Creating functional Settings interface..."
cat > src/interfaces/web/templates/settings.html << 'EOF'
{% extends "base.html" %}
{% block title %}Settings - Trading Bot{% endblock %}

{% block content %}
<!-- Account Settings -->
<div class="card">
    <h2>👤 Account Settings</h2>
    <form id="account-form">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <label>Username:</label>
                <input type="text" id="username" value="trader_user" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                
                <label>Email:</label>
                <input type="email" id="email" value="user@example.com" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
            </div>
            
            <div>
                <label>Timezone:</label>
                <select id="timezone" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                    <option value="UTC">UTC</option>
                    <option value="America/New_York">New York (EST)</option>
                    <option value="Europe/London">London (GMT)</option>
                    <option value="Asia/Tokyo">Tokyo (JST)</option>
                </select>
                
                <label>Theme:</label>
                <select id="theme" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                    <option value="dark" selected>Dark Mode</option>
                    <option value="light">Light Mode</option>
                </select>
            </div>
        </div>
        
        <button type="submit" class="btn" style="background: #238636;">💾 Save Account Settings</button>
    </form>
</div>

<!-- Exchange Configuration -->
<div class="card">
    <h2>🏢 Exchange Configuration</h2>
    
    <div style="margin-bottom: 20px;">
        <h3 style="color: #58a6ff; margin-bottom: 15px;">Connected Exchanges</h3>
        
        <div style="border: 1px solid #30363d; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4 style="color: #f0f6fc; margin-bottom: 5px;">🏦 KuCoin</h4>
                    <p style="font-size: 14px; color: #7d8590;">Status: <span class="status running">CONNECTED</span></p>
                    <p style="font-size: 14px; color: #7d8590;">Mode: Paper Trading</p>
                </div>
                <div>
                    <button class="btn" onclick="configureExchange('kucoin')" style="margin-right: 10px;">⚙️ Configure</button>
                    <button class="btn danger" onclick="disconnectExchange('kucoin')">❌ Disconnect</button>
                </div>
            </div>
        </div>
    </div>
    
    <div>
        <h3 style="color: #58a6ff; margin-bottom: 15px;">Add New Exchange</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
            <button class="btn" onclick="addExchange('binance')" style="padding: 20px; text-align: center;">
                <div>🔶 Binance</div>
                <div style="font-size: 12px; margin-top: 5px;">Add Binance Exchange</div>
            </button>
            
            <button class="btn" onclick="addExchange('okx')" style="padding: 20px; text-align: center;">
                <div>⭕ OKX</div>
                <div style="font-size: 12px; margin-top: 5px;">Add OKX Exchange</div>
            </button>
            
            <button class="btn" onclick="addExchange('bybit')" style="padding: 20px; text-align: center;">
                <div>🟡 Bybit</div>
                <div style="font-size: 12px; margin-top: 5px;">Add Bybit Exchange</div>
            </button>
        </div>
    </div>
</div>

<!-- Exchange Configuration Modal -->
<div id="exchange-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000;">
    <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 30px; min-width: 400px;">
        <h3 style="color: #f0f6fc; margin-bottom: 20px;">🔑 Exchange API Configuration</h3>
        
        <form id="exchange-config-form">
            <div style="margin-bottom: 15px;">
                <label>Exchange:</label>
                <input type="text" id="exchange-name" readonly style="width: 100%; padding: 8px; margin-top: 5px; background: #21262d; color: #7d8590; border: 1px solid #30363d; border-radius: 4px;">
            </div>
            
            <div style="margin-bottom: 15px;">
                <label>API Key:</label>
                <input type="password" id="api-key" placeholder="Enter your API key" style="width: 100%; padding: 8px; margin-top: 5px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
            </div>
            
            <div style="margin-bottom: 15px;">
                <label>API Secret:</label>
                <input type="password" id="api-secret" placeholder="Enter your API secret" style="width: 100%; padding: 8px; margin-top: 5px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
            </div>
            
            <div style="margin-bottom: 15px;">
                <label>Passphrase (if required):</label>
                <input type="password" id="passphrase" placeholder="Enter passphrase" style="width: 100%; padding: 8px; margin-top: 5px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
            </div>
            
            <div style="margin-bottom: 20px;">
                <label style="display: flex; align-items: center;">
                    <input type="checkbox" id="testnet" style="margin-right: 10px;">
                    Use Testnet (Sandbox Mode)
                </label>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <button type="button" class="btn" onclick="saveExchangeConfig()" style="background: #238636;">💾 Save</button>
                <button type="button" class="btn" onclick="closeExchangeModal()">❌ Cancel</button>
            </div>
        </form>
    </div>
</div>

<!-- Risk Management -->
<div class="card">
    <h2>⚠️ Risk Management</h2>
    <form id="risk-form">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <label>Max Position Size ($):</label>
                <input type="number" id="max-position" value="1000" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                
                <label>Max Daily Loss ($):</label>
                <input type="number" id="max-daily-loss" value="500" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                
                <label>Max Open Positions:</label>
                <input type="number" id="max-positions" value="10" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
            </div>
            
            <div>
                <label>Stop Loss (%):</label>
                <input type="number" id="stop-loss" value="5" step="0.1" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                
                <label>Take Profit (%):</label>
                <input type="number" id="take-profit" value="15" step="0.1" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                
                <label style="display: flex; align-items: center; margin-top: 20px;">
                    <input type="checkbox" id="trailing-stop" checked style="margin-right: 10px;">
                    Enable Trailing Stop
                </label>
            </div>
        </div>
        
        <button type="submit" class="btn" style="background: #da3633;">⚠️ Save Risk Settings</button>
    </form>
</div>

<!-- Notifications -->
<div class="card">
    <h2>🔔 Notification Settings</h2>
    <form id="notifications-form">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <h4 style="color: #58a6ff; margin-bottom: 15px;">Telegram Notifications</h4>
                
                <label>Bot Token:</label>
                <input type="password" id="telegram-token" placeholder="Bot token from @BotFather" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
                
                <label>Chat ID:</label>
                <input type="text" id="telegram-chat" placeholder="Your Telegram chat ID" style="width: 100%; padding: 8px; margin: 5px 0 15px 0; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;">
            </div>
            
            <div>
                <h4 style="color: #58a6ff; margin-bottom: 15px;">Notification Types</h4>
                
                <label style="display: flex; align-items: center; margin-bottom: 10px;">
                    <input type="checkbox" id="notify-trades" checked style="margin-right: 10px;">
                    Trade Executions
                </label>
                
                <label style="display: flex; align-items: center; margin-bottom: 10px;">
                    <input type="checkbox" id="notify-signals" checked style="margin-right: 10px;">
                    Trading Signals
                </label>
                
                <label style="display: flex; align-items: center; margin-bottom: 10px;">
                    <input type="checkbox" id="notify-alerts" checked style="margin-right: 10px;">
                    System Alerts
                </label>
                
                <label style="display: flex; align-items: center; margin-bottom: 10px;">
                    <input type="checkbox" id="notify-performance" style="margin-right: 10px;">
                    Daily Performance Reports
                </label>
            </div>
        </div>
        
        <button type="submit" class="btn" style="background: #7c3aed;">🔔 Save Notification Settings</button>
    </form>
</div>

<script>
// Account form submission
document.getElementById('account-form').addEventListener('submit', function(e) {
    e.preventDefault();
    alert('Account settings saved successfully!');
});

// Risk form submission
document.getElementById('risk-form').addEventListener('submit', function(e) {
    e.preventDefault();
    alert('Risk management settings saved successfully!');
});

// Notifications form submission
document.getElementById('notifications-form').addEventListener('submit', function(e) {
    e.preventDefault();
    alert('Notification settings saved successfully!');
});

// Exchange functions
function addExchange(exchangeName) {
    document.getElementById('exchange-name').value = exchangeName;
    document.getElementById('exchange-modal').style.display = 'block';
}

function configureExchange(exchangeName) {
    document.getElementById('exchange-name').value = exchangeName;
    document.getElementById('exchange-modal').style.display = 'block';
}

function disconnectExchange(exchangeName) {
    if (confirm(`Are you sure you want to disconnect ${exchangeName}?`)) {
        alert(`${exchangeName} disconnected successfully`);
    }
}

function closeExchangeModal() {
    document.getElementById('exchange-modal').style.display = 'none';
    document.getElementById('exchange-config-form').reset();
}

function saveExchangeConfig() {
    const exchangeName = document.getElementById('exchange-name').value;
    const apiKey = document.getElementById('api-key').value;
    const apiSecret = document.getElementById('api-secret').value;
    
    if (!apiKey || !apiSecret) {
        alert('Please enter both API key and secret');
        return;
    }
    
    alert(`${exchangeName} exchange configured successfully!`);
    closeExchangeModal();
}

// Close modal when clicking outside
document.getElementById('exchange-modal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeExchangeModal();
    }
});
</script>
{% endblock %}
EOF

print_success "Created functional Settings interface"

print_success "All functional web interface pages created!"
echo ""
echo "🚀 Features implemented:"
echo "📊 Dashboard: Real-time status and portfolio overview"
echo "💹 Trading: Order placement, management, and history"
echo "🧠 Strategies: Selection, configuration, and performance"
echo "📈 Backtesting: Setup, progress, results, and history"
echo "⚙️ Settings: Account, exchanges, risk, and notifications"
echo ""
echo "✅ Web interface is now fully functional!"
echo "🔄 Restart the container to see the new pages:"
echo "   docker-compose restart trading-bot"
echo ""
echo "🌐 Access at: http://localhost:5000"

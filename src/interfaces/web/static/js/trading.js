// src/interfaces/web/static/js/trading.js

/**
 * Updated Trading Interface JavaScript with Real API Integration
 * Connects frontend to actual backend APIs instead of mock data
 */

class TradingInterface {
    constructor() {
        this.currentSymbol = 'BTC/USDT';
        this.currentExchange = 'kucoin';
        this.isRefreshing = false;
        this.wsConnection = null;
        this.authToken = localStorage.getItem('access_token');
        
        this.initializeInterface();
        this.setupEventListeners();
        this.startRealTimeUpdates();
        this.loadInitialData();
    }

    // Authentication and API utilities
    getAuthHeaders() {
        const token = localStorage.getItem('access_token');
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        };
    }

    async makeAuthenticatedRequest(url, options = {}) {
        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    ...this.getAuthHeaders(),
                    ...options.headers
                }
            });

            if (response.status === 401) {
                // Token expired, redirect to login
                localStorage.removeItem('access_token');
                window.location.href = '/login';
                return null;
            }

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            this.showError(`API request failed: ${error.message}`);
            return null;
        }
    }

    // Initialize interface components
    initializeInterface() {
        console.log('Initializing trading interface...');
        
        // Check authentication
        if (!this.authToken) {
            window.location.href = '/login';
            return;
        }

        // Initialize components
        this.initializeSymbolSelector();
        this.initializeOrderForms();
        this.initializeOrderBook();
        this.initializeTradeHistory();
        this.initializePortfolio();
    }

    setupEventListeners() {
        // Symbol selector
        const symbolSelect = document.getElementById('symbol-select');
        if (symbolSelect) {
            symbolSelect.addEventListener('change', (e) => {
                this.currentSymbol = e.target.value;
                this.refreshMarketData();
            });
        }

        // Exchange selector
        const exchangeSelect = document.getElementById('exchange-select');
        if (exchangeSelect) {
            exchangeSelect.addEventListener('change', (e) => {
                this.currentExchange = e.target.value;
                this.refreshMarketData();
            });
        }

        // Order forms
        const buyForm = document.getElementById('buy-form');
        if (buyForm) {
            buyForm.addEventListener('submit', (e) => this.handleBuyOrder(e));
        }

        const sellForm = document.getElementById('sell-form');
        if (sellForm) {
            sellForm.addEventListener('submit', (e) => this.handleSellOrder(e));
        }

        // Refresh button
        const refreshBtn = document.getElementById('refresh-market-data');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshMarketData());
        }

        // Order type toggles
        document.querySelectorAll('input[name="buy-type"]').forEach(radio => {
            radio.addEventListener('change', (e) => this.toggleOrderType('buy', e.target.value));
        });

        document.querySelectorAll('input[name="sell-type"]').forEach(radio => {
            radio.addEventListener('change', (e) => this.toggleOrderType('sell', e.target.value));
        });
    }

    // Real-time WebSocket connection
    startRealTimeUpdates() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/updates`;
            
            this.wsConnection = new WebSocket(wsUrl);
            
            this.wsConnection.onopen = () => {
                console.log('WebSocket connected');
                this.updateConnectionStatus(true);
            };
            
            this.wsConnection.onmessage = (event) => {
                this.handleRealTimeUpdate(event.data);
            };
            
            this.wsConnection.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus(false);
                // Reconnect after 5 seconds
                setTimeout(() => this.startRealTimeUpdates(), 5000);
            };
            
            this.wsConnection.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
            
        } catch (error) {
            console.error('Error starting real-time updates:', error);
        }
    }

    handleRealTimeUpdate(data) {
        try {
            if (data.startsWith('price_update:')) {
                const [, symbol, price] = data.split(':');
                this.updateSymbolPrice(symbol, parseFloat(price));
            }
        } catch (error) {
            console.error('Error handling real-time update:', error);
        }
    }

    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connection-status');
        if (statusEl) {
            statusEl.textContent = connected ? 'Connected' : 'Disconnected';
            statusEl.className = connected ? 'status-connected' : 'status-disconnected';
        }
    }

    updateSymbolPrice(symbol, price) {
        if (symbol === this.currentSymbol) {
            const priceEl = document.getElementById('current-price');
            if (priceEl) {
                priceEl.textContent = `$${price.toLocaleString()}`;
            }
        }
    }

    // Load initial data
    async loadInitialData() {
        try {
            console.log('Loading initial trading data...');
            
            await Promise.all([
                this.refreshMarketData(),
                this.refreshPortfolio(),
                this.refreshOpenOrders(),
                this.refreshTradeHistory()
            ]);
            
            console.log('Initial data loaded successfully');
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load trading data');
        }
    }

    // Market data
    async refreshMarketData() {
        if (this.isRefreshing) return;
        
        try {
            this.isRefreshing = true;
            this.showLoadingState('market-data');
            
            const data = await this.makeAuthenticatedRequest(
                `/api/trading/market-data/${this.currentSymbol}?exchange=${this.currentExchange}`
            );
            
            if (data) {
                this.updateMarketData(data);
            }
        } catch (error) {
            console.error('Error refreshing market data:', error);
            this.showError('Failed to refresh market data');
        } finally {
            this.isRefreshing = false;
            this.hideLoadingState('market-data');
        }
    }

    updateMarketData(data) {
        // Update current price
        const priceEl = document.getElementById('current-price');
        if (priceEl) {
            priceEl.textContent = `$${data.price.toLocaleString()}`;
        }

        // Update 24h change
        const changeEl = document.getElementById('price-change-24h');
        if (changeEl) {
            const changeClass = data.change_24h_pct >= 0 ? 'positive' : 'negative';
            const changeSign = data.change_24h_pct >= 0 ? '+' : '';
            changeEl.textContent = `${changeSign}${data.change_24h_pct.toFixed(2)}%`;
            changeEl.className = `price-change ${changeClass}`;
        }

        // Update volume
        const volumeEl = document.getElementById('volume-24h');
        if (volumeEl) {
            volumeEl.textContent = `$${data.volume_24h.toLocaleString()}`;
        }

        // Update high/low
        const highEl = document.getElementById('high-24h');
        if (highEl) {
            highEl.textContent = `$${data.high_24h.toLocaleString()}`;
        }

        const lowEl = document.getElementById('low-24h');
        if (lowEl) {
            lowEl.textContent = `$${data.low_24h.toLocaleString()}`;
        }

        // Update timestamp
        const timestampEl = document.getElementById('last-update');
        if (timestampEl) {
            timestampEl.textContent = `Last updated: ${new Date(data.timestamp).toLocaleTimeString()}`;
        }
    }

    // Portfolio management
    async refreshPortfolio() {
        try {
            const data = await this.makeAuthenticatedRequest(
                `/api/trading/portfolio?exchange=${this.currentExchange}`
            );
            
            if (data) {
                this.updatePortfolio(data);
            }
        } catch (error) {
            console.error('Error refreshing portfolio:', error);
        }
    }

    updatePortfolio(data) {
        // Update total balance
        const totalBalanceEl = document.getElementById('total-balance');
        if (totalBalanceEl) {
            totalBalanceEl.textContent = `$${data.total_balance.toLocaleString()}`;
        }

        // Update available balance
        const availableBalanceEl = document.getElementById('available-balance');
        if (availableBalanceEl) {
            availableBalanceEl.textContent = `$${data.available_balance.toLocaleString()}`;
        }

        // Update used balance
        const usedBalanceEl = document.getElementById('used-balance');
        if (usedBalanceEl) {
            usedBalanceEl.textContent = `$${data.used_balance.toLocaleString()}`;
        }

        // Update PnL
        if (data.pnl_24h !== undefined) {
            const pnlEl = document.getElementById('pnl-24h');
            if (pnlEl) {
                const pnlClass = data.pnl_24h >= 0 ? 'positive' : 'negative';
                const pnlSign = data.pnl_24h >= 0 ? '+' : '';
                pnlEl.textContent = `${pnlSign}$${data.pnl_24h.toFixed(2)}`;
                pnlEl.className = `pnl ${pnlClass}`;
            }
        }

        // Update positions table
        this.updatePositionsTable(data.positions);
    }

    updatePositionsTable(positions) {
        const tbody = document.getElementById('positions-table-body');
        if (!tbody) return;

        tbody.innerHTML = '';

        positions.forEach(position => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${position.asset}</td>
                <td>${position.total.toFixed(8)}</td>
                <td>${position.free.toFixed(8)}</td>
                <td>${position.used.toFixed(8)}</td>
                <td>$${position.usd_value.toFixed(2)}</td>
            `;
            tbody.appendChild(row);
        });
    }

    // Order management
    async handleBuyOrder(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const orderData = {
            symbol: this.currentSymbol,
            side: 'buy',
            type: formData.get('buy-type'),
            amount: parseFloat(formData.get('buy-amount')),
            exchange: this.currentExchange
        };

        if (orderData.type === 'limit') {
            orderData.price = parseFloat(formData.get('buy-price'));
        }

        await this.placeOrder(orderData);
    }

    async handleSellOrder(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const orderData = {
            symbol: this.currentSymbol,
            side: 'sell',
            type: formData.get('sell-type'),
            amount: parseFloat(formData.get('sell-amount')),
            exchange: this.currentExchange
        };

        if (orderData.type === 'limit') {
            orderData.price = parseFloat(formData.get('sell-price'));
        }

        await this.placeOrder(orderData);
    }

    async placeOrder(orderData) {
        try {
            // Show confirmation dialog
            const confirmMessage = `Place ${orderData.side} order for ${orderData.amount} ${orderData.symbol.split('/')[0]}?`;
            if (!confirm(confirmMessage)) {
                return;
            }

            this.showLoadingState('order-placement');

            const response = await this.makeAuthenticatedRequest('/api/trading/order', {
                method: 'POST',
                body: JSON.stringify(orderData)
            });

            if (response) {
                this.showSuccess(`${orderData.side} order placed successfully!`);
                
                // Reset form
                const form = orderData.side === 'buy' ? 
                    document.getElementById('buy-form') : 
                    document.getElementById('sell-form');
                if (form) form.reset();

                // Refresh data
                await Promise.all([
                    this.refreshPortfolio(),
                    this.refreshOpenOrders(),
                    this.refreshTradeHistory()
                ]);
            }
        } catch (error) {
            console.error('Error placing order:', error);
            this.showError(`Failed to place ${orderData.side} order`);
        } finally {
            this.hideLoadingState('order-placement');
        }
    }

    // Open orders
    async refreshOpenOrders() {
        try {
            const data = await this.makeAuthenticatedRequest(
                `/api/trading/orders?exchange=${this.currentExchange}`
            );
            
            if (data) {
                this.updateOpenOrdersTable(data);
            }
        } catch (error) {
            console.error('Error refreshing open orders:', error);
        }
    }

    updateOpenOrdersTable(orders) {
        const tbody = document.getElementById('open-orders-table-body');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (!orders || orders.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center">No open orders</td></tr>';
            return;
        }

        orders.forEach(order => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${order.symbol}</td>
                <td><span class="order-side order-side-${order.side}">${order.side.toUpperCase()}</span></td>
                <td>${order.type.toUpperCase()}</td>
                <td>${order.amount}</td>
                <td>$${order.price ? order.price.toFixed(2) : 'Market'}</td>
                <td><span class="order-status order-status-${order.status}">${order.status}</span></td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="tradingInterface.cancelOrder('${order.id}')">
                        Cancel
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    async cancelOrder(orderId) {
        try {
            if (!confirm('Are you sure you want to cancel this order?')) {
                return;
            }

            const response = await this.makeAuthenticatedRequest(
                `/api/trading/orders/${orderId}?exchange=${this.currentExchange}`,
                { method: 'DELETE' }
            );

            if (response) {
                this.showSuccess('Order cancelled successfully!');
                await this.refreshOpenOrders();
            }
        } catch (error) {
            console.error('Error cancelling order:', error);
            this.showError('Failed to cancel order');
        }
    }

    // Trade history
    async refreshTradeHistory() {
        try {
            const data = await this.makeAuthenticatedRequest(
                `/api/trading/trades?limit=50&symbol=${this.currentSymbol}`
            );
            
            if (data) {
                this.updateTradeHistoryTable(data);
            }
        } catch (error) {
            console.error('Error refreshing trade history:', error);
        }
    }

    updateTradeHistoryTable(trades) {
        const tbody = document.getElementById('trade-history-table-body');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (!trades || trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center">No trade history</td></tr>';
            return;
        }

        trades.forEach(trade => {
            const row = document.createElement('tr');
            const pnlDisplay = trade.pnl ? 
                `<span class="pnl ${trade.pnl >= 0 ? 'positive' : 'negative'}">
                    ${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)}
                </span>` : '-';

            row.innerHTML = `
                <td>${new Date(trade.timestamp).toLocaleString()}</td>
                <td>${trade.symbol}</td>
                <td><span class="trade-side trade-side-${trade.side}">${trade.side.toUpperCase()}</span></td>
                <td>${trade.amount}</td>
                <td>$${trade.price.toFixed(2)}</td>
                <td><span class="trade-status trade-status-${trade.status}">${trade.status}</span></td>
                <td>${pnlDisplay}</td>
            `;
            tbody.appendChild(row);
        });
    }

    // UI utilities
    toggleOrderType(side, type) {
        const priceField = document.getElementById(`${side}-price-field`);
        if (priceField) {
            priceField.style.display = type === 'limit' ? 'block' : 'none';
        }
    }

    showLoadingState(component) {
        const spinner = document.getElementById(`${component}-spinner`);
        if (spinner) {
            spinner.style.display = 'inline-block';
        }
    }

    hideLoadingState(component) {
        const spinner = document.getElementById(`${component}-spinner`);
        if (spinner) {
            spinner.style.display = 'none';
        }
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        // Add to page
        document.body.appendChild(notification);

        // Show notification
        setTimeout(() => notification.classList.add('show'), 100);

        // Hide and remove after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => document.body.removeChild(notification), 300);
        }, 5000);
    }

    // Initialize components
    initializeSymbolSelector() {
        const symbolSelect = document.getElementById('symbol-select');
        if (symbolSelect) {
            // Add popular trading pairs
            const symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'DOT/USDT'];
            symbols.forEach(symbol => {
                const option = document.createElement('option');
                option.value = symbol;
                option.textContent = symbol;
                option.selected = symbol === this.currentSymbol;
                symbolSelect.appendChild(option);
            });
        }
    }

    initializeOrderForms() {
        // Set default order types
        const marketBuyRadio = document.querySelector('input[name="buy-type"][value="market"]');
        if (marketBuyRadio) marketBuyRadio.checked = true;

        const marketSellRadio = document.querySelector('input[name="sell-type"][value="market"]');
        if (marketSellRadio) marketSellRadio.checked = true;

        // Hide price fields initially
        this.toggleOrderType('buy', 'market');
        this.toggleOrderType('sell', 'market');
    }

    initializeOrderBook() {
        // Order book functionality can be added here
        console.log('Order book initialized');
    }

    initializeTradeHistory() {
        // Trade history functionality
        console.log('Trade history initialized');
    }

    initializePortfolio() {
        // Portfolio functionality
        console.log('Portfolio initialized');
    }
}

// Initialize trading interface when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.tradingInterface = new TradingInterface();
});

// Add CSS for notifications
const notificationStyles = `
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 4px;
        color: white;
        font-weight: 500;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
        z-index: 1000;
        max-width: 400px;
    }

    .notification.show {
        opacity: 1;
        transform: translateX(0);
    }

    .notification-success {
        background-color: #10b981;
    }

    .notification-error {
        background-color: #ef4444;
    }

    .order-side-buy {
        color: #10b981;
        font-weight: 600;
    }

    .order-side-sell {
        color: #ef4444;
        font-weight: 600;
    }

    .trade-side-buy {
        color: #10b981;
        font-weight: 600;
    }

    .trade-side-sell {
        color: #ef4444;
        font-weight: 600;
    }

    .pnl.positive {
        color: #10b981;
    }

    .pnl.negative {
        color: #ef4444;
    }

    .price-change.positive {
        color: #10b981;
    }

    .price-change.negative {
        color: #ef4444;
    }

    .status-connected {
        color: #10b981;
    }

    .status-disconnected {
        color: #ef4444;
    }

    .order-status-open {
        color: #3b82f6;
    }

    .order-status-filled {
        color: #10b981;
    }

    .order-status-cancelled {
        color: #6b7280;
    }

    .trade-status-filled {
        color: #10b981;
    }

    .trade-status-pending {
        color: #f59e0b;
    }
`;

// Add styles to head
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);

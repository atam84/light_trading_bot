// web/static/js/websocket.js

/**
 * WebSocket Client for Real-time Features
 * Handles live price updates, trade notifications, and portfolio changes
 */

class WebSocketClient {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.subscriptions = new Set();
        this.messageHandlers = new Map();
        
        this.init();
    }

    init() {
        this.setupEventHandlers();
        this.connect();
    }

    setupEventHandlers() {
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.handlePageHidden();
            } else {
                this.handlePageVisible();
            }
        });

        // Handle before page unload
        window.addEventListener('beforeunload', () => {
            this.disconnect();
        });

        // Register default message handlers
        this.onMessage('connection', (data) => {
            console.log('WebSocket connected:', data.message);
            this.showConnectionStatus('Connected', 'success');
        });

        this.onMessage('price_update', (data) => {
            this.handlePriceUpdate(data);
        });

        this.onMessage('trade_executed', (data) => {
            this.handleTradeExecuted(data);
        });

        this.onMessage('strategy_signal', (data) => {
            this.handleStrategySignal(data);
        });

        this.onMessage('portfolio_update', (data) => {
            this.handlePortfolioUpdate(data);
        });

        this.onMessage('backtest_complete', (data) => {
            this.handleBacktestComplete(data);
        });

        this.onMessage('system_alert', (data) => {
            this.handleSystemAlert(data);
        });

        this.onMessage('error', (data) => {
            console.error('WebSocket error:', data.message);
            this.showConnectionStatus('Error: ' + data.message, 'error');
        });
    }

    connect() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            return;
        }

        // Get authentication token
        const token = this.getAuthToken();
        if (!token) {
            console.warn('No auth token found, WebSocket connection skipped');
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/connect?token=${token}`;

        try {
            this.socket = new WebSocket(wsUrl);
            this.setupSocketEventHandlers();
            this.showConnectionStatus('Connecting...', 'info');
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.handleConnectionError();
        }
    }

    setupSocketEventHandlers() {
        this.socket.onopen = () => {
            console.log('WebSocket connection opened');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            
            // Resubscribe to topics
            this.resubscribe();
        };

        this.socket.onclose = (event) => {
            console.log('WebSocket connection closed:', event.code, event.reason);
            this.isConnected = false;
            this.showConnectionStatus('Disconnected', 'warning');
            
            // Attempt to reconnect unless it was a manual close
            if (event.code !== 1000) {
                this.scheduleReconnect();
            }
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.handleConnectionError();
        };

        this.socket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error, event.data);
            }
        };
    }

    handleMessage(message) {
        const { type, ...data } = message;
        
        // Call registered handler
        const handler = this.messageHandlers.get(type);
        if (handler) {
            handler(data);
        } else {
            console.log('Unhandled message type:', type, data);
        }
    }

    onMessage(type, handler) {
        this.messageHandlers.set(type, handler);
    }

    send(message) {
        if (this.isConnected && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(message));
            return true;
        } else {
            console.warn('WebSocket not connected, message not sent:', message);
            return false;
        }
    }

    subscribe(topic) {
        this.subscriptions.add(topic);
        return this.send({
            type: 'subscribe',
            topic: topic
        });
    }

    unsubscribe(topic) {
        this.subscriptions.delete(topic);
        return this.send({
            type: 'unsubscribe',
            topic: topic
        });
    }

    resubscribe() {
        this.subscriptions.forEach(topic => {
            this.send({
                type: 'subscribe',
                topic: topic
            });
        });
    }

    ping() {
        return this.send({ type: 'ping' });
    }

    getPortfolio() {
        return this.send({ type: 'get_portfolio' });
    }

    getActiveTrades() {
        return this.send({ type: 'get_active_trades' });
    }

    disconnect() {
        if (this.socket) {
            this.socket.close(1000, 'Manual disconnect');
            this.socket = null;
        }
        this.isConnected = false;
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.showConnectionStatus('Connection failed', 'error');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff
        
        console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            if (!this.isConnected) {
                this.connect();
            }
        }, delay);
    }

    handleConnectionError() {
        this.isConnected = false;
        this.showConnectionStatus('Connection error', 'error');
    }

    handlePageHidden() {
        // Reduce activity when page is hidden
        console.log('Page hidden, reducing WebSocket activity');
    }

    handlePageVisible() {
        // Resume full activity when page is visible
        console.log('Page visible, resuming WebSocket activity');
        
        if (!this.isConnected) {
            this.connect();
        } else {
            // Refresh data
            this.getPortfolio();
            this.getActiveTrades();
        }
    }

    getAuthToken() {
        // Try to get token from various sources
        
        // 1. From meta tag
        const metaToken = document.querySelector('meta[name="auth-token"]');
        if (metaToken) {
            return metaToken.getAttribute('content');
        }

        // 2. From localStorage
        const localToken = localStorage.getItem('auth_token');
        if (localToken) {
            return localToken;
        }

        // 3. From cookie (simplified)
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'auth_token') {
                return value;
            }
        }

        return null;
    }

    showConnectionStatus(message, type) {
        const statusElement = document.getElementById('connection-status');
        if (!statusElement) return;

        const colors = {
            success: 'bg-green-500',
            warning: 'bg-yellow-500',
            error: 'bg-red-500',
            info: 'bg-blue-500'
        };

        statusElement.className = `fixed bottom-4 right-4 text-white px-4 py-2 rounded-lg shadow-lg ${colors[type] || colors.info}`;
        statusElement.textContent = message;
        statusElement.classList.remove('hidden');

        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(() => {
                statusElement.classList.add('hidden');
            }, 3000);
        }
    }

    // Message Handlers
    handlePriceUpdate(data) {
        const { symbol, price, change_24h } = data;
        
        // Update price displays
        document.querySelectorAll(`[data-symbol="${symbol}"]`).forEach(element => {
            const priceElement = element.querySelector('.price');
            const changeElement = element.querySelector('.change');
            
            if (priceElement) {
                priceElement.textContent = this.formatPrice(price);
                
                // Add price animation
                priceElement.classList.add('price-updated');
                setTimeout(() => {
                    priceElement.classList.remove('price-updated');
                }, 1000);
            }
            
            if (changeElement) {
                changeElement.textContent = this.formatPercentage(change_24h);
                changeElement.className = `change ${change_24h >= 0 ? 'text-green-500' : 'text-red-500'}`;
            }
        });

        // Update charts if visible
        this.updatePriceCharts(symbol, price);
    }

    handleTradeExecuted(data) {
        const { trade_data } = data;
        
        // Show notification
        if (window.app) {
            const message = `${trade_data.side.toUpperCase()} ${trade_data.amount} ${trade_data.symbol} at ${this.formatPrice(trade_data.price)}`;
            window.app.showMessage(message, 'success');
        }

        // Update trade tables
        this.refreshTradeDisplays();
        
        // Play notification sound (if enabled)
        this.playNotificationSound('trade');
    }

    handleStrategySignal(data) {
        const { signal_data } = data;
        
        // Show signal notification
        if (window.app) {
            const message = `Strategy Signal: ${signal_data.action} ${signal_data.symbol}`;
            window.app.showMessage(message, 'info');
        }

        // Update strategy displays
        this.updateStrategyIndicators(signal_data);
    }

    handlePortfolioUpdate(data) {
        const portfolioData = data.data;
        
        // Update portfolio metrics
        if (portfolioData) {
            this.updatePortfolioDisplay(portfolioData);
        }
    }

    handleBacktestComplete(data) {
        const { backtest_data } = data;
        
        // Show completion notification
        if (window.app) {
            window.app.showMessage('Backtest completed successfully', 'success');
        }

        // Redirect to results if on backtest page
        if (window.location.pathname.includes('backtesting')) {
            setTimeout(() => {
                window.location.href = `/backtesting/result/${backtest_data.backtest_id}`;
            }, 2000);
        }
    }

    handleSystemAlert(data) {
        const { alert_data } = data;
        
        // Show system alert
        if (window.app) {
            window.app.showMessage(alert_data.message, 'warning');
        }

        // Play alert sound
        this.playNotificationSound('alert');
    }

    // Helper Methods
    formatPrice(price) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 6
        }).format(price);
    }

    formatPercentage(value) {
        return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
    }

    updatePriceCharts(symbol, price) {
        // Update Chart.js charts
        document.querySelectorAll(`canvas[data-symbol="${symbol}"]`).forEach(canvas => {
            const chart = Chart.getChart(canvas);
            if (chart && chart.data.datasets.length > 0) {
                const dataset = chart.data.datasets[0];
                const now = new Date();
                
                // Add new data point
                dataset.data.push({
                    x: now,
                    y: price
                });
                
                // Remove old data points (keep last 100)
                if (dataset.data.length > 100) {
                    dataset.data.shift();
                }
                
                chart.update('none');
            }
        });
    }

    refreshTradeDisplays() {
        // Refresh trade tables and lists
        const tradeElements = document.querySelectorAll('[data-auto-refresh="trades"]');
        tradeElements.forEach(element => {
            // Trigger refresh
            const refreshEvent = new CustomEvent('refresh-trades');
            element.dispatchEvent(refreshEvent);
        });
    }

    updateStrategyIndicators(signalData) {
        // Update strategy status indicators
        const strategyElements = document.querySelectorAll(`[data-strategy-id="${signalData.strategy_id}"]`);
        strategyElements.forEach(element => {
            const indicator = element.querySelector('.strategy-indicator');
            if (indicator) {
                indicator.classList.add('signal-active');
                setTimeout(() => {
                    indicator.classList.remove('signal-active');
                }, 3000);
            }
        });
    }

    updatePortfolioDisplay(portfolioData) {
        // Update portfolio metrics in DOM
        Object.entries(portfolioData).forEach(([key, value]) => {
            const element = document.getElementById(`portfolio-${key}`);
            if (element) {
                if (typeof value === 'number') {
                    element.textContent = key.includes('pct') ? 
                        this.formatPercentage(value) : 
                        this.formatPrice(value);
                } else {
                    element.textContent = value;
                }
            }
        });
    }

    playNotificationSound(type) {
        // Only play if user has interacted with page and sounds are enabled
        if (!this.userHasInteracted || !this.soundsEnabled) return;

        const sounds = {
            trade: '/static/sounds/trade.mp3',
            alert: '/static/sounds/alert.mp3',
            signal: '/static/sounds/signal.mp3'
        };

        const soundFile = sounds[type];
        if (soundFile) {
            const audio = new Audio(soundFile);
            audio.volume = 0.3;
            audio.play().catch(error => {
                console.log('Could not play notification sound:', error);
            });
        }
    }

    // Settings
    enableSounds() {
        this.soundsEnabled = true;
        localStorage.setItem('notification_sounds', 'true');
    }

    disableSounds() {
        this.soundsEnabled = false;
        localStorage.setItem('notification_sounds', 'false');
    }

    get soundsEnabled() {
        return localStorage.getItem('notification_sounds') !== 'false';
    }

    set soundsEnabled(value) {
        localStorage.setItem('notification_sounds', value.toString());
    }
}

// Initialize WebSocket client
let wsClient;
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if user is authenticated
    const userElement = document.querySelector('[data-user-authenticated]');
    if (userElement) {
        wsClient = new WebSocketClient();
        
        // Make available globally
        window.wsClient = wsClient;
    }
});

// Track user interaction for sound notifications
document.addEventListener('click', () => {
    if (wsClient) {
        wsClient.userHasInteracted = true;
    }
}, { once: true });

// Export for use in other modules
window.WebSocketClient = WebSocketClient;
"""
Trading Bot Web Interface using Flask.
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import logging
import time
import os

logger = logging.getLogger(__name__)

def create_app():
    """Create Flask application."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Enable CORS for API endpoints
    CORS(app)
    
    @app.route('/')
    def dashboard():
        """Main dashboard."""
        return render_template('dashboard.html')
    
    @app.route('/health')
    def health():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "service": "trading_bot_web",
            "timestamp": time.time()
        })
    
    @app.route('/api/status')
    def api_status():
        """Bot status API."""
        return jsonify({
            "bot_status": "running",
            "mode": "paper",
            "strategy": "active",
            "symbol": "BTC/USDT",
            "web_interface": "flask"
        })
    
    @app.route('/api/balance')
    def api_balance():
        """Account balance API."""
        return jsonify({
            "total_balance": 10000.0,
            "available_balance": 9500.0,
            "currency": "USDT",
            "mode": "paper_trading"
        })
    
    @app.route('/api/trades')
    def api_trades():
        """Recent trades API."""
        return jsonify({
            "trades": [
                {
                    "id": "1",
                    "symbol": "BTC/USDT",
                    "side": "buy",
                    "amount": 0.001,
                    "price": 42000,
                    "timestamp": time.time() - 3600
                }
            ],
            "total": 1
        })
    
    @app.route('/trading')
    def trading():
        """Trading interface."""
        return render_template('trading.html')
    
    @app.route('/strategies')
    def strategies():
        """Strategy management."""
        return render_template('strategies.html')
    
    @app.route('/backtesting')
    def backtesting():
        """Backtesting interface."""
        return render_template('backtesting.html')
    
    @app.route('/settings')
    def settings():
        """Settings page."""
        return render_template('settings.html')
    
    logger.info("Flask web application created")
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

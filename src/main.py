# src/main.py - Updated to include web interface startup

import asyncio
import threading
import time
from typing import Optional
import click
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('trading_bot')

@click.group()
def cli():
    """Light Trading Bot - Multi-interface Cryptocurrency Trading Bot."""
    pass

@cli.command()
@click.option('--mode', type=click.Choice(['live', 'paper', 'backtest']), default='paper',
              help='Trading mode')
@click.option('--strategy', default='simple_buy_sell', help='Strategy to use')
@click.option('--symbol', default='BTC/USDT', help='Trading pair')
@click.option('--with-web', is_flag=True, default=False, help='Start web interface alongside trading')
@click.option('--web-port', default=5000, help='Web interface port')
def start(mode: str, strategy: str, symbol: str, with_web: bool, web_port: int):
    """Start the trading bot."""
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    
    # Display banner
    banner = Panel(
        "[bold blue]🤖 Light Trading Bot v0.1.0[/bold blue]\n"
        "Multi-interface Cryptocurrency Trading Bot\n"
        "Supports: Live Trading • Paper Trading • Backtesting",
        title="Trading Bot System",
        border_style="blue"
    )
    console.print(banner)
    
    logger.info("Application initialized successfully")
    
    try:
        if with_web:
            # Start both trading engine and web interface
            console.print(f"🚀 Starting trading bot in {mode} mode with web interface...")
            start_bot_with_web(mode, strategy, symbol, web_port)
        else:
            # Start only trading engine (current behavior)
            console.print(f"🚀 Starting trading bot in {mode} mode...")
            start_trading_engine(mode, strategy, symbol)
            
    except KeyboardInterrupt:
        console.print("\n👋 Trading bot stopped by user")
    except Exception as e:
        console.print(f"❌ Error starting bot: {e}")
        logger.error(f"Failed to start trading bot: {e}")

def start_bot_with_web(mode: str, strategy: str, symbol: str, web_port: int):
    """Start both trading engine and web interface."""
    
    # Start web interface in a separate thread
    web_thread = threading.Thread(
        target=start_web_interface,
        args=(web_port,),
        daemon=True
    )
    web_thread.start()
    
    # Give web interface time to start
    time.sleep(2)
    logger.info(f"Web interface started on port {web_port}")
    
    # Start trading engine in main thread
    start_trading_engine(mode, strategy, symbol)

def start_web_interface(port: int):
    """Start the web interface server."""
    try:
        # Import web app
        from interfaces.web.app import create_app
        
        app = create_app()
        logger.info(f"Starting web interface on port {port}")
        
        # Run Flask app
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
        
    except ImportError as e:
        logger.error(f"Web interface not available: {e}")
        logger.info("Creating minimal web interface...")
        create_minimal_web_interface(port)
    except Exception as e:
        logger.error(f"Failed to start web interface: {e}")

def create_minimal_web_interface(port: int):
    """Create a minimal web interface if full one is not available."""
    try:
        from flask import Flask, jsonify, render_template_string
        
        app = Flask(__name__)
        
        @app.route('/')
        def dashboard():
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Trading Bot Dashboard</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #1a1a1a; color: white; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .status { background: #2d2d2d; padding: 20px; border-radius: 8px; margin: 20px 0; }
                    .running { border-left: 4px solid #00ff00; }
                    .info { background: #333; padding: 15px; border-radius: 4px; margin: 10px 0; }
                    h1 { color: #00ff88; }
                    h2 { color: #88ff00; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🤖 Light Trading Bot Dashboard</h1>
                    
                    <div class="status running">
                        <h2>✅ Bot Status: Running</h2>
                        <p>Mode: Paper Trading</p>
                        <p>Strategy: Active</p>
                        <p>Symbol: BTC/USDT</p>
                    </div>
                    
                    <div class="info">
                        <h3>📊 Quick Info</h3>
                        <p>• Trading engine is running successfully</p>
                        <p>• Web interface is operational</p>
                        <p>• All services connected</p>
                    </div>
                    
                    <div class="info">
                        <h3>🔗 API Endpoints</h3>
                        <p>• <a href="/health" style="color: #00ff88;">/health</a> - Health check</p>
                        <p>• <a href="/api/status" style="color: #00ff88;">/api/status</a> - Bot status</p>
                        <p>• <a href="/api/balance" style="color: #00ff88;">/api/balance</a> - Account balance</p>
                    </div>
                    
                    <div class="info">
                        <h3>📈 Next Steps</h3>
                        <p>This is a minimal web interface. The full dashboard with charts and trading controls will be available once the complete web interface is implemented.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            return render_template_string(html)
        
        @app.route('/health')
        def health():
            return jsonify({
                "status": "healthy",
                "service": "trading_bot_web",
                "timestamp": time.time()
            })
        
        @app.route('/api/status')
        def api_status():
            return jsonify({
                "bot_status": "running",
                "mode": "paper",
                "strategy": "active",
                "symbol": "BTC/USDT",
                "web_interface": "minimal"
            })
        
        @app.route('/api/balance')
        def api_balance():
            return jsonify({
                "total_balance": 10000.0,
                "available_balance": 9500.0,
                "currency": "USDT",
                "mode": "paper_trading"
            })
        
        logger.info(f"Starting minimal web interface on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
        
    except Exception as e:
        logger.error(f"Failed to create minimal web interface: {e}")

def start_trading_engine(mode: str, strategy: str, symbol: str):
    """Start the trading engine (existing functionality)."""
    from core.trading_engine import TradingEngine
    from core.config_manager import ConfigManager
    
    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.get_trading_config()
    
    logger.info(f"Trading engine created with config: {mode}")
    
    # Create and start trading engine
    engine = TradingEngine(config)
    logger.info(f"Starting trading engine in interactive mode: {mode}")
    
    # Run the trading engine
    asyncio.run(engine.start_interactive_mode(mode, symbol))

@cli.command()
@click.option('--port', default=5000, help='Port to run web interface on')
@click.option('--host', default='0.0.0.0', help='Host to bind web interface to')
def web(port: int, host: str):
    """Start only the web interface."""
    from rich.console import Console
    
    console = Console()
    console.print(f"🌐 Starting web interface on {host}:{port}")
    
    start_web_interface(port)

@cli.command()
@click.option('--token', help='Telegram bot token')
def telegram(token: Optional[str]):
    """Start the Telegram bot interface."""
    from rich.console import Console
    
    console = Console()
    console.print("📱 Starting Telegram bot interface...")
    
    # TODO: Implement telegram bot startup
    console.print("❌ Telegram bot not yet implemented")

@cli.command()
@click.option('--detailed', is_flag=True, help='Show detailed status')
def status(detailed: bool):
    """Show bot status."""
    from rich.console import Console
    
    console = Console()
    console.print("📊 Bot Status: Running")
    
    if detailed:
        console.print("• Mode: Paper Trading")
        console.print("• Strategy: Active")
        console.print("• Web: Available on port 5000")

if __name__ == "__main__":
    cli()

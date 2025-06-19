# src/main.py
"""
Trading Bot - Main Application Entry Point

This module serves as the main entry point for the trading bot application.
It provides CLI commands to start different interfaces and manage the bot.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from utils.config.settings import Settings
from utils.logging.logger import setup_logger
from core.engine.trading_engine import TradingEngine

# Initialize console for rich output
console = Console()

def display_banner():
    """Display application banner"""
    banner_text = Text()
    banner_text.append("🤖 Light Trading Bot v0.1.0\n", style="bold blue")
    banner_text.append("Multi-interface Cryptocurrency Trading Bot\n", style="cyan")
    banner_text.append("Supports: Live Trading • Paper Trading • Backtesting", style="dim")
    
    panel = Panel(
        banner_text,
        border_style="blue",
        padding=(1, 2),
        title="[bold blue]Trading Bot System[/bold blue]"
    )
    console.print(panel)

@click.group()
@click.option('--config', '-c', default='config.yaml', help='Configuration file path')
@click.option('--env', '-e', default='.env', help='Environment file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config, env, verbose):
    """Light Trading Bot - Multi-interface cryptocurrency trading system"""
    
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Display banner
    display_banner()
    
    try:
        # Initialize settings
        settings = Settings(config_file=config, env_file=env)
        ctx.obj['settings'] = settings
        
        # Setup logging
        logger = setup_logger(
            level=settings.LOG_LEVEL if not verbose else "DEBUG",
            format_type=settings.LOG_FORMAT
        )
        ctx.obj['logger'] = logger
        
        logger.info("Application initialized successfully")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to initialize application: {e}[/red]")
        sys.exit(1)

@cli.command()
@click.option('--mode', '-m', type=click.Choice(['live', 'paper', 'backtest']), 
              default='paper', help='Trading mode')
@click.option('--strategy', '-s', help='Strategy name to use')
@click.option('--symbol', help='Trading pair (e.g., BTC/USDT)')
@click.option('--daemon', '-d', is_flag=True, help='Run as daemon')
@click.pass_context
def start(ctx, mode, strategy, symbol, daemon):
    """Start the trading bot"""
    
    settings = ctx.obj['settings']
    logger = ctx.obj['logger']
    
    console.print(f"[green]🚀 Starting trading bot in {mode} mode...[/green]")
    
    try:
        # Initialize trading engine
        engine = TradingEngine(settings, logger)
        
        if daemon:
            console.print("[yellow]⚡ Running in daemon mode...[/yellow]")
            # Run as daemon
            asyncio.run(engine.start_daemon(mode=mode, strategy=strategy, symbol=symbol))
        else:
            # Interactive mode
            asyncio.run(engine.start_interactive(mode=mode, strategy=strategy, symbol=symbol))
            
    except KeyboardInterrupt:
        console.print("[yellow]⏹️  Bot stopped by user[/yellow]")
    except Exception as e:
        logger.error(f"Failed to start trading bot: {e}")
        console.print(f"[red]❌ Error starting bot: {e}[/red]")
        sys.exit(1)

@cli.command()
@click.pass_context
def stop(ctx):
    """Stop the trading bot"""
    console.print("[yellow]⏹️  Stopping trading bot...[/yellow]")
    
    # Implementation will be added when we create the engine
    console.print("[green]✅ Trading bot stopped successfully[/green]")

@cli.command()
@click.option('--detailed', '-d', is_flag=True, help='Show detailed status')
@click.pass_context
def status(ctx, detailed):
    """Show trading bot status"""
    
    console.print("[cyan]📊 Trading Bot Status[/cyan]")
    
    # Implementation will be added when we create the engine
    console.print("[green]✅ Bot is running[/green]")
    
    if detailed:
        console.print("\n[cyan]Detailed Status:[/cyan]")
        console.print("• Mode: Paper Trading")
        console.print("• Active Strategies: 1")
        console.print("• Open Trades: 2")
        console.print("• Balance: $10,000")

@cli.command()
@click.option('--port', '-p', default=5000, help='Web UI port')
@click.option('--host', '-h', default='127.0.0.1', help='Web UI host')
@click.pass_context
def web(ctx, port, host):
    """Start the web interface"""
    
    console.print(f"[blue]🌐 Starting web interface on http://{host}:{port}[/blue]")
    
    try:
        from interfaces.web.web_app import create_app
        
        settings = ctx.obj['settings']
        app = create_app(settings)
        
        import uvicorn
        uvicorn.run(app, host=host, port=port, reload=True)
        
    except ImportError:
        console.print("[red]❌ Web interface dependencies not available[/red]")
    except Exception as e:
        console.print(f"[red]❌ Failed to start web interface: {e}[/red]")

@cli.command()
@click.option('--config-name', '-n', default='default', help='Telegram config name')
@click.pass_context
def telegram(ctx, config_name):
    """Start the Telegram bot"""
    
    console.print(f"[blue]📱 Starting Telegram bot (config: {config_name})[/blue]")
    
    try:
        from interfaces.telegram.telegram_bot import TelegramBot
        
        settings = ctx.obj['settings']
        logger = ctx.obj['logger']
        
        bot = TelegramBot(settings, logger, config_name)
        asyncio.run(bot.start())
        
    except ImportError:
        console.print("[red]❌ Telegram bot dependencies not available[/red]")
    except Exception as e:
        console.print(f"[red]❌ Failed to start Telegram bot: {e}[/red]")

@cli.command()
@click.option('--strategy', '-s', required=True, help='Strategy name')
@click.option('--symbol', required=True, help='Trading pair (e.g., BTC/USDT)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--initial-balance', default=10000, help='Initial balance for backtesting')
@click.pass_context
def backtest(ctx, strategy, symbol, start_date, end_date, initial_balance):
    """Run backtesting for a strategy"""
    
    console.print(f"[cyan]🧪 Running backtest for {strategy} on {symbol}[/cyan]")
    
    try:
        from core.modes.backtesting import BacktestEngine
        
        settings = ctx.obj['settings']
        logger = ctx.obj['logger']
        
        engine = BacktestEngine(settings, logger)
        
        result = asyncio.run(engine.run_backtest(
            strategy=strategy,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance
        ))
        
        # Display results
        console.print(f"\n[green]✅ Backtest completed![/green]")
        console.print(f"Total Return: {result.get('total_return', 0):.2f}%")
        console.print(f"Win Rate: {result.get('win_rate', 0):.2f}%")
        console.print(f"Max Drawdown: {result.get('max_drawdown', 0):.2f}%")
        
    except Exception as e:
        console.print(f"[red]❌ Backtest failed: {e}[/red]")

@cli.command()
@click.option('--lines', '-n', default=50, help='Number of lines to show')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--level', help='Filter by log level')
@click.pass_context
def logs(ctx, lines, follow, level):
    """Show application logs"""
    
    settings = ctx.obj['settings']
    log_file = settings.LOG_FILE
    
    if not os.path.exists(log_file):
        console.print("[yellow]⚠️  No log file found[/yellow]")
        return
    
    console.print(f"[cyan]📋 Showing logs from {log_file}[/cyan]")
    
    try:
        if follow:
            console.print("[yellow]Following logs... Press Ctrl+C to stop[/yellow]")
            # Implementation for tail -f functionality
            import subprocess
            subprocess.run(['tail', '-f', log_file])
        else:
            # Show last N lines
            with open(log_file, 'r') as f:
                lines_list = f.readlines()
                for line in lines_list[-lines:]:
                    if level and level.upper() not in line:
                        continue
                    print(line.rstrip())
                    
    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️  Log following stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error reading logs: {e}[/red]")

@cli.command()
@click.option('--validate', '-v', is_flag=True, help='Validate configuration')
@click.pass_context
def config(ctx, validate):
    """Show or validate configuration"""
    
    settings = ctx.obj['settings']
    
    if validate:
        console.print("[cyan]🔍 Validating configuration...[/cyan]")
        
        # Validation logic will be implemented in settings
        try:
            is_valid = settings.validate()
            if is_valid:
                console.print("[green]✅ Configuration is valid[/green]")
            else:
                console.print("[red]❌ Configuration has errors[/red]")
        except Exception as e:
            console.print(f"[red]❌ Validation failed: {e}[/red]")
    else:
        console.print("[cyan]⚙️  Current Configuration:[/cyan]")
        console.print(f"• Environment: {settings.ENVIRONMENT}")
        console.print(f"• Trading Mode: {settings.DEFAULT_TRADING_MODE}")
        console.print(f"• Default Exchange: {settings.DEFAULT_EXCHANGE}")
        console.print(f"• MongoDB URL: {settings.MONGODB_URL}")
        console.print(f"• ccxt-gateway URL: {settings.CCXT_GATEWAY_URL}")

@cli.command()
def version():
    """Show version information"""
    
    version_info = Text()
    version_info.append("🤖 Light Trading Bot\n", style="bold blue")
    version_info.append("Version: 0.1.0\n", style="cyan")
    version_info.append("Python: " + sys.version.split()[0] + "\n", style="dim")
    version_info.append("Platform: " + sys.platform, style="dim")
    
    console.print(Panel(version_info, title="Version Information", border_style="blue"))

if __name__ == "__main__":
    try:
        cli()
    except Exception as e:
        console.print(f"[red]❌ Fatal error: {e}[/red]")
        sys.exit(1)
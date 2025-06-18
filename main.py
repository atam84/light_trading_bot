# main.py

"""
Trading Bot - Main Entry Point

This is the main entry point for the trading bot application.
Supports multiple interface modes: CLI, Web, and Telegram Bot.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import click
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init(autoreset=True)

@click.group()
@click.version_option(version="0.1.0")
def main():
    """🤖 Trading Bot - Advanced cryptocurrency trading automation
    
    Available interfaces:
    • CLI: Command-line interface with colored output
    • Web: Flask/FastAPI dashboard (coming soon)
    • Telegram: Bot interface for remote control (coming soon)
    """
    pass

@main.command()
def cli():
    """🖥️ Start CLI interface"""
    try:
        from src.interfaces.cli.cli_main import cli as cli_interface
        
        # Print welcome message
        click.echo(f"\n{Fore.CYAN}🤖 Trading Bot CLI Interface{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}Use 'python main.py cli --help' for available commands{Style.RESET_ALL}\n")
        
        # Start CLI interface
        cli_interface()
        
    except ImportError as e:
        click.echo(f"{Fore.RED}❌ Failed to import CLI interface: {e}{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}❌ CLI interface error: {e}{Style.RESET_ALL}")
        sys.exit(1)

@main.command()
def web():
    """🌐 Start Web interface"""
    click.echo(f"{Fore.YELLOW}⚠️ Web interface coming soon...{Style.RESET_ALL}")
    # TODO: Implement web interface startup

@main.command()
def telegram():
    """📱 Start Telegram Bot interface"""
    click.echo(f"{Fore.YELLOW}⚠️ Telegram Bot interface coming soon...{Style.RESET_ALL}")
    # TODO: Implement telegram bot startup

@main.command()
@click.option('--mode', type=click.Choice(['live', 'paper', 'backtest']), 
              default='paper', help='Trading mode')
@click.option('--interface', type=click.Choice(['cli', 'web', 'telegram']), 
              default='cli', help='Interface to use')
def run(mode: str, interface: str):
    """🚀 Quick start trading bot with specified mode and interface"""
    try:
        click.echo(f"\n{Fore.CYAN}🚀 Starting Trading Bot{Style.RESET_ALL}")
        click.echo(f"Mode: {Fore.GREEN}{mode.upper()}{Style.RESET_ALL}")
        click.echo(f"Interface: {Fore.GREEN}{interface.upper()}{Style.RESET_ALL}\n")
        
        if interface == 'cli':
            from src.interfaces.cli.cli_main import cli as cli_interface
            # Start bot with CLI
            click.echo(f"{Fore.INFO}Use 'bot start --mode {mode}' to start trading{Style.RESET_ALL}")
            cli_interface()
        elif interface == 'web':
            click.echo(f"{Fore.YELLOW}⚠️ Web interface coming soon...{Style.RESET_ALL}")
        elif interface == 'telegram':
            click.echo(f"{Fore.YELLOW}⚠️ Telegram interface coming soon...{Style.RESET_ALL}")
            
    except ImportError as e:
        click.echo(f"{Fore.RED}❌ Failed to import interface: {e}{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}❌ Startup error: {e}{Style.RESET_ALL}")
        sys.exit(1)

@main.command()
def setup():
    """⚙️ Setup and configuration wizard"""
    click.echo(f"\n{Fore.CYAN}⚙️ Trading Bot Setup Wizard{Style.RESET_ALL}")
    
    # Check environment
    click.echo("Checking environment...")
    
    # Check .env file
    env_file = Path(".env")
    if not env_file.exists():
        click.echo(f"{Fore.YELLOW}⚠️ .env file not found. Copy .env.example to .env{Style.RESET_ALL}")
    else:
        click.echo(f"{Fore.GREEN}✅ .env file found{Style.RESET_ALL}")
    
    # Check config file
    config_file = Path("config.yaml")
    if not config_file.exists():
        click.echo(f"{Fore.YELLOW}⚠️ config.yaml file not found{Style.RESET_ALL}")
    else:
        click.echo(f"{Fore.GREEN}✅ config.yaml file found{Style.RESET_ALL}")
    
    # Check data directory
    data_dir = Path("data")
    if not data_dir.exists():
        click.echo(f"{Fore.YELLOW}⚠️ Creating data directory...{Style.RESET_ALL}")
        data_dir.mkdir(exist_ok=True)
        click.echo(f"{Fore.GREEN}✅ Data directory created{Style.RESET_ALL}")
    else:
        click.echo(f"{Fore.GREEN}✅ Data directory exists{Style.RESET_ALL}")
    
    # Check logs directory
    logs_dir = Path("logs")
    if not logs_dir.exists():
        click.echo(f"{Fore.YELLOW}⚠️ Creating logs directory...{Style.RESET_ALL}")
        logs_dir.mkdir(exist_ok=True)
        click.echo(f"{Fore.GREEN}✅ Logs directory created{Style.RESET_ALL}")
    else:
        click.echo(f"{Fore.GREEN}✅ Logs directory exists{Style.RESET_ALL}")
    
    click.echo(f"\n{Fore.GREEN}✅ Setup complete!{Style.RESET_ALL}")
    click.echo(f"Next steps:")
    click.echo(f"1. Configure your .env file with API keys")
    click.echo(f"2. Adjust config.yaml settings")
    click.echo(f"3. Run: python main.py run --mode paper")

@main.command()
def status():
    """📊 Show system status"""
    click.echo(f"\n{Fore.CYAN}📊 Trading Bot System Status{Style.RESET_ALL}")
    
    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    click.echo(f"Python Version: {Fore.GREEN}{python_version}{Style.RESET_ALL}")
    
    # Check platform
    click.echo(f"Platform: {Fore.GREEN}{sys.platform}{Style.RESET_ALL}")
    
    # Check working directory
    click.echo(f"Working Directory: {Fore.GREEN}{os.getcwd()}{Style.RESET_ALL}")
    
    # Check key files
    key_files = [".env", "config.yaml", "requirements.txt", "docker-compose.yml"]
    click.echo(f"\n{Fore.CYAN}File Status:{Style.RESET_ALL}")
    for file in key_files:
        if Path(file).exists():
            click.echo(f"  {Fore.GREEN}✅ {file}{Style.RESET_ALL}")
        else:
            click.echo(f"  {Fore.RED}❌ {file}{Style.RESET_ALL}")
    
    # Check directories
    key_dirs = ["src", "data", "logs", "tests"]
    click.echo(f"\n{Fore.CYAN}Directory Status:{Style.RESET_ALL}")
    for dir_name in key_dirs:
        if Path(dir_name).exists():
            click.echo(f"  {Fore.GREEN}✅ {dir_name}/{Style.RESET_ALL}")
        else:
            click.echo(f"  {Fore.RED}❌ {dir_name}/{Style.RESET_ALL}")

@main.command()
def test():
    """🧪 Run tests"""
    try:
        import pytest
        click.echo(f"\n{Fore.CYAN}🧪 Running Tests{Style.RESET_ALL}")
        
        # Run pytest
        exit_code = pytest.main([
            "tests/",
            "-v",
            "--tb=short",
            "--color=yes"
        ])
        
        if exit_code == 0:
            click.echo(f"\n{Fore.GREEN}✅ All tests passed!{Style.RESET_ALL}")
        else:
            click.echo(f"\n{Fore.RED}❌ Some tests failed!{Style.RESET_ALL}")
            
    except ImportError:
        click.echo(f"{Fore.RED}❌ pytest not installed. Run: pip install pytest{Style.RESET_ALL}")
    except Exception as e:
        click.echo(f"{Fore.RED}❌ Test execution error: {e}{Style.RESET_ALL}")

@main.command()
def docs():
    """📚 Open documentation"""
    click.echo(f"\n{Fore.CYAN}📚 Trading Bot Documentation{Style.RESET_ALL}")
    click.echo(f"README: ./README.md")
    click.echo(f"API Docs: ./docs/api.md")
    click.echo(f"Strategies: ./docs/strategies.md")
    click.echo(f"Configuration: ./docs/configuration.md")

# Alternative entry points for direct CLI access
@main.command(context_settings=dict(ignore_unknown_options=True))
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def bot(args):
    """🤖 Direct bot commands (shortcut to CLI)"""
    try:
        from src.interfaces.cli.cli_main import cli as cli_interface
        
        # Pass arguments to CLI
        sys.argv = ['cli'] + list(args)
        cli_interface()
        
    except ImportError as e:
        click.echo(f"{Fore.RED}❌ Failed to import CLI: {e}{Style.RESET_ALL}")
    except Exception as e:
        click.echo(f"{Fore.RED}❌ Bot command error: {e}{Style.RESET_ALL}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        click.echo(f"\n{Fore.YELLOW}⚠️ Operation cancelled by user{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        click.echo(f"{Fore.RED}❌ Unexpected error: {e}{Style.RESET_ALL}")
        sys.exit(1)

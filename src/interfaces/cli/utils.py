# src/interfaces/cli/utils.py

import json
import csv
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import pandas as pd
from colorama import Fore, Back, Style
import click

class CLIFormatter:
    """Utility class for CLI formatting and display"""
    
    @staticmethod
    def format_table(data: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> str:
        """Format data as a table for CLI display"""
        if not data:
            return "No data to display"
        
        if not headers:
            headers = list(data[0].keys())
        
        # Calculate column widths
        widths = {}
        for header in headers:
            widths[header] = max(
                len(str(header)),
                max(len(str(row.get(header, ''))) for row in data)
            )
        
        # Create table
        table_lines = []
        
        # Header
        header_line = " | ".join(f"{header:<{widths[header]}}" for header in headers)
        table_lines.append(f"{Fore.CYAN}{header_line}{Style.RESET_ALL}")
        
        # Separator
        separator = "-+-".join("-" * widths[header] for header in headers)
        table_lines.append(separator)
        
        # Data rows
        for row in data:
            row_line = " | ".join(f"{str(row.get(header, '')):<{widths[header]}}" for header in headers)
            table_lines.append(row_line)
        
        return "\n".join(table_lines)
    
    @staticmethod
    def format_json(data: Dict[str, Any], indent: int = 2) -> str:
        """Format JSON data with syntax highlighting"""
        json_str = json.dumps(data, indent=indent, default=str)
        return f"{Fore.GREEN}{json_str}{Style.RESET_ALL}"
    
    @staticmethod
    def format_percentage(value: float, precision: int = 2) -> str:
        """Format percentage with color coding"""
        formatted = f"{value:.{precision}f}%"
        if value > 0:
            return f"{Fore.GREEN}+{formatted}{Style.RESET_ALL}"
        elif value < 0:
            return f"{Fore.RED}{formatted}{Style.RESET_ALL}"
        else:
            return formatted
    
    @staticmethod
    def format_currency(amount: float, currency: str = "USD", precision: int = 2) -> str:
        """Format currency with color coding"""
        symbol = "$" if currency == "USD" else currency
        formatted = f"{symbol}{abs(amount):,.{precision}f}"
        
        if amount > 0:
            return f"{Fore.GREEN}{formatted}{Style.RESET_ALL}"
        elif amount < 0:
            return f"{Fore.RED}-{formatted}{Style.RESET_ALL}"
        else:
            return formatted
    
    @staticmethod
    def format_status(status: str) -> str:
        """Format status with appropriate icons and colors"""
        status_map = {
            'active': f"{Fore.GREEN}🟢 Active{Style.RESET_ALL}",
            'inactive': f"{Fore.RED}🔴 Inactive{Style.RESET_ALL}",
            'running': f"{Fore.GREEN}🟢 Running{Style.RESET_ALL}",
            'stopped': f"{Fore.RED}🛑 Stopped{Style.RESET_ALL}",
            'error': f"{Fore.RED}❌ Error{Style.RESET_ALL}",
            'warning': f"{Fore.YELLOW}⚠️ Warning{Style.RESET_ALL}",
            'success': f"{Fore.GREEN}✅ Success{Style.RESET_ALL}",
            'pending': f"{Fore.YELLOW}⏳ Pending{Style.RESET_ALL}",
            'completed': f"{Fore.GREEN}✅ Completed{Style.RESET_ALL}",
            'cancelled': f"{Fore.RED}❌ Cancelled{Style.RESET_ALL}"
        }
        return status_map.get(status.lower(), status)

class CLIExporter:
    """Utility class for exporting CLI data"""
    
    @staticmethod
    def export_to_csv(data: List[Dict[str, Any]], filename: str) -> bool:
        """Export data to CSV file"""
        try:
            if not data:
                return False
            
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            return True
        except Exception:
            return False
    
    @staticmethod
    def export_to_json(data: Any, filename: str) -> bool:
        """Export data to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception:
            return False
    
    @staticmethod
    def export_backtest_report(results: Dict[str, Any], filename: str) -> bool:
        """Export backtest results as formatted report"""
        try:
            with open(filename, 'w') as f:
                f.write("TRADING BOT BACKTEST REPORT\n")
                f.write("=" * 50 + "\n\n")
                
                f.write(f"Strategy: {results.get('strategy_name', 'Unknown')}\n")
                f.write(f"Symbol: {results.get('symbol', 'Unknown')}\n")
                f.write(f"Timeframe: {results.get('timeframe', 'Unknown')}\n")
                f.write(f"Start Date: {results.get('start_date', 'Unknown')}\n")
                f.write(f"End Date: {results.get('end_date', 'Unknown')}\n\n")
                
                f.write("PERFORMANCE METRICS\n")
                f.write("-" * 20 + "\n")
                f.write(f"Initial Balance: ${results.get('initial_balance', 0):,.2f}\n")
                f.write(f"Final Balance: ${results.get('final_balance', 0):,.2f}\n")
                f.write(f"Total Return: {results.get('total_return_pct', 0):.2f}%\n")
                f.write(f"Total Trades: {results.get('total_trades', 0)}\n")
                f.write(f"Win Rate: {results.get('win_rate', 0):.2f}%\n")
                f.write(f"Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}\n")
                f.write(f"Max Drawdown: {results.get('max_drawdown', 0):.2f}%\n\n")
                
                if 'trades_log' in results:
                    f.write("TRADE LOG\n")
                    f.write("-" * 10 + "\n")
                    for trade in results['trades_log']:
                        f.write(f"{trade.get('timestamp', '')} - "
                               f"{trade.get('side', '').upper()} "
                               f"{trade.get('amount', 0)} {trade.get('symbol', '')} "
                               f"@ ${trade.get('price', 0):.2f}\n")
                
            return True
        except Exception:
            return False

class CLIValidator:
    """Utility class for CLI input validation"""
    
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """Validate trading symbol format"""
        if not symbol:
            return False
        return '/' in symbol and len(symbol.split('/')) == 2
    
    @staticmethod
    def validate_amount(amount: str) -> tuple[bool, float]:
        """Validate amount input"""
        try:
            value = float(amount)
            return value > 0, value
        except ValueError:
            return False, 0.0
    
    @staticmethod
    def validate_price(price: str) -> tuple[bool, float]:
        """Validate price input"""
        try:
            value = float(price)
            return value > 0, value
        except ValueError:
            return False, 0.0
    
    @staticmethod
    def validate_timeframe(timeframe: str) -> bool:
        """Validate timeframe format"""
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '8h', '1d', '1w']
        return timeframe in valid_timeframes
    
    @staticmethod
    def validate_date(date_str: str) -> tuple[bool, Optional[datetime]]:
        """Validate date string format"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return True, date_obj
        except ValueError:
            return False, None

class CLIProgress:
    """Utility class for showing progress in CLI operations"""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
    
    def update(self, increment: int = 1):
        """Update progress"""
        self.current += increment
        self._show_progress()
    
    def _show_progress(self):
        """Display progress bar"""
        if self.total == 0:
            return
        
        percentage = (self.current / self.total) * 100
        bar_length = 40
        filled_length = int(bar_length * self.current / self.total)
        
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        click.echo(f"\r{self.description}: |{bar}| {percentage:.1f}% "
                  f"({self.current}/{self.total})", nl=False)
        
        if self.current >= self.total:
            click.echo()  # New line when complete

class CLIColorScheme:
    """Color scheme constants for CLI"""
    
    # Status colors
    SUCCESS = Fore.GREEN
    ERROR = Fore.RED
    WARNING = Fore.YELLOW
    INFO = Fore.CYAN
    HEADER = Fore.MAGENTA
    
    # Data colors
    POSITIVE = Fore.GREEN
    NEGATIVE = Fore.RED
    NEUTRAL = Fore.WHITE
    
    # UI elements
    BORDER = Fore.BLUE
    HIGHLIGHT = Fore.YELLOW
    
    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Apply color to text"""
        return f"{color}{text}{Style.RESET_ALL}"

def confirm_action(message: str, default: bool = False) -> bool:
    """Enhanced confirmation prompt with colors"""
    default_text = "Y/n" if default else "y/N"
    prompt = f"{Fore.YELLOW}⚠️ {message} [{default_text}]: {Style.RESET_ALL}"
    
    response = click.prompt(prompt, default="", show_default=False)
    
    if not response:
        return default
    
    return response.lower() in ['y', 'yes', 'true', '1']

def show_spinner(message: str):
    """Show a simple spinner for long operations"""
    import itertools
    import time
    import threading
    
    spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    
    def spin():
        while getattr(spin, 'running', True):
            click.echo(f"\r{next(spinner)} {message}", nl=False)
            time.sleep(0.1)
    
    thread = threading.Thread(target=spin)
    thread.daemon = True
    thread.start()
    
    return thread

def stop_spinner(thread):
    """Stop the spinner"""
    if hasattr(thread, 'running'):
        thread.running = False
    click.echo("\r" + " " * 50 + "\r", nl=False)  # Clear spinner line

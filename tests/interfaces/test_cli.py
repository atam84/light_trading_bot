# tests/interfaces/test_cli.py

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from click.testing import CliRunner
import json

from src.interfaces.cli.cli_main import cli, TradingBotCLI
from src.interfaces.cli.utils import CLIFormatter, CLIValidator, CLIExporter
from src.core.engine.mode_manager import TradingMode

class TestTradingBotCLI:
    """Test cases for TradingBotCLI class"""
    
    @pytest.fixture
    def cli_instance(self):
        """Create CLI instance for testing"""
        with patch('src.interfaces.cli.cli_main.ConfigManager'), \
             patch('src.interfaces.cli.cli_main.Logger'), \
             patch('src.interfaces.cli.cli_main.RepositoryManager'), \
             patch('src.interfaces.cli.cli_main.APIClientManager'):
            return TradingBotCLI()
    
    def test_print_methods(self, cli_instance, capsys):
        """Test CLI print methods"""
        cli_instance.print_success("Success message")
        cli_instance.print_error("Error message")
        cli_instance.print_warning("Warning message")
        cli_instance.print_info("Info message")
        
        captured = capsys.readouterr()
        assert "Success message" in captured.out
        assert "Error message" in captured.out
        assert "Warning message" in captured.out
        assert "Info message" in captured.out
    
    def test_format_currency(self, cli_instance):
        """Test currency formatting"""
        positive = cli_instance.format_currency(100.50)
        negative = cli_instance.format_currency(-50.25)
        zero = cli_instance.format_currency(0.00)
        
        assert "$100.50" in positive
        assert "$50.25" in negative
        assert "$0.00" in zero
    
    def test_format_percentage(self, cli_instance):
        """Test percentage formatting"""
        positive = cli_instance.format_percentage(15.5)
        negative = cli_instance.format_percentage(-8.2)
        zero = cli_instance.format_percentage(0.0)
        
        assert "+15.50%" in positive
        assert "-8.20%" in negative
        assert "0.00%" in zero

class TestCLICommands:
    """Test cases for CLI commands"""
    
    @pytest.fixture
    def runner(self):
        """Create CLI runner for testing"""
        return CliRunner()
    
    def test_version_command(self, runner):
        """Test version command"""
        result = runner.invoke(cli, ['version'])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
    
    @patch('src.interfaces.cli.cli_main.cli_instance')
    def test_bot_status_command(self, mock_cli, runner):
        """Test bot status command"""
        mock_cli.initialize = AsyncMock()
        mock_cli.engine = Mock()
        mock_cli.engine.is_running = True
        mock_cli.engine.get_status = AsyncMock(return_value={
            'mode': 'PAPER',
            'uptime': '1h 30m',
            'active_strategies': 2,
            'open_trades': 5
        })
        
        result = runner.invoke(cli, ['bot', 'status'])
        assert result.exit_code == 0
        # Note: In real test, would need to handle async properly
    
    def test_config_show_command(self, runner):
        """Test config show command"""
        with patch('src.interfaces.cli.cli_main.cli_instance') as mock_cli:
            mock_cli.config.get_all_config.return_value = {
                'trading': {'mode': 'paper', 'fee_rate': 0.0005},
                'risk': {'max_trades': 10}
            }
            
            result = runner.invoke(cli, ['config', 'show'])
            assert result.exit_code == 0
    
    @patch('src.interfaces.cli.cli_main.cli_instance')
    def test_strategies_list_command(self, mock_cli, runner):
        """Test strategies list command"""
        mock_cli.initialize = AsyncMock()
        mock_cli.repository.strategies.get_user_strategies = AsyncMock(return_value=[
            {
                'name': 'RSI Strategy',
                'strategy_type': 'indicator',
                'active': True,
                'description': 'RSI-based trading strategy'
            }
        ])
        
        result = runner.invoke(cli, ['strategies', 'list'])
        assert result.exit_code == 0

class TestCLIFormatter:
    """Test cases for CLI formatting utilities"""
    
    def test_format_table(self):
        """Test table formatting"""
        data = [
            {'name': 'BTC/USDT', 'price': 42000, 'change': 2.5},
            {'name': 'ETH/USDT', 'price': 3000, 'change': -1.2}
        ]
        
        table = CLIFormatter.format_table(data)
        assert 'BTC/USDT' in table
        assert 'ETH/USDT' in table
        assert '42000' in table
        assert '3000' in table
    
    def test_format_json(self):
        """Test JSON formatting"""
        data = {'key1': 'value1', 'key2': 42}
        formatted = CLIFormatter.format_json(data)
        assert 'key1' in formatted
        assert 'value1' in formatted
    
    def test_format_percentage(self):
        """Test percentage formatting"""
        positive = CLIFormatter.format_percentage(15.5)
        negative = CLIFormatter.format_percentage(-8.2)
        zero = CLIFormatter.format_percentage(0.0)
        
        assert "+15.50%" in positive
        assert "-8.20%" in negative
        assert "0.00%" in zero
    
    def test_format_currency(self):
        """Test currency formatting"""
        usd = CLIFormatter.format_currency(1000.50)
        btc = CLIFormatter.format_currency(0.5, 'BTC', 4)
        
        assert "$1,000.50" in usd
        assert "BTC0.5000" in btc
    
    def test_format_status(self):
        """Test status formatting"""
        active = CLIFormatter.format_status('active')
        error = CLIFormatter.format_status('error')
        
        assert '🟢' in active
        assert 'Active' in active
        assert '❌' in error
        assert 'Error' in error

class TestCLIValidator:
    """Test cases for CLI validation utilities"""
    
    def test_validate_symbol(self):
        """Test symbol validation"""
        assert CLIValidator.validate_symbol('BTC/USDT') == True
        assert CLIValidator.validate_symbol('ETH/BTC') == True
        assert CLIValidator.validate_symbol('BTCUSDT') == False
        assert CLIValidator.validate_symbol('') == False
        assert CLIValidator.validate_symbol('BTC/') == False
    
    def test_validate_amount(self):
        """Test amount validation"""
        valid, amount = CLIValidator.validate_amount('10.5')
        assert valid == True
        assert amount == 10.5
        
        valid, amount = CLIValidator.validate_amount('0')
        assert valid == False
        
        valid, amount = CLIValidator.validate_amount('invalid')
        assert valid == False
    
    def test_validate_price(self):
        """Test price validation"""
        valid, price = CLIValidator.validate_price('42000.50')
        assert valid == True
        assert price == 42000.50
        
        valid, price = CLIValidator.validate_price('-100')
        assert valid == False
        
        valid, price = CLIValidator.validate_price('not_a_number')
        assert valid == False
    
    def test_validate_timeframe(self):
        """Test timeframe validation"""
        assert CLIValidator.validate_timeframe('1h') == True
        assert CLIValidator.validate_timeframe('4h') == True
        assert CLIValidator.validate_timeframe('1d') == True
        assert CLIValidator.validate_timeframe('2h') == False
        assert CLIValidator.validate_timeframe('invalid') == False
    
    def test_validate_date(self):
        """Test date validation"""
        valid, date = CLIValidator.validate_date('2024-01-15')
        assert valid == True
        assert date is not None
        
        valid, date = CLIValidator.validate_date('invalid-date')
        assert valid == False
        assert date is None

class TestCLIExporter:
    """Test cases for CLI export utilities"""
    
    def test_export_to_json(self, tmp_path):
        """Test JSON export"""
        data = {'test': 'data', 'number': 42}
        file_path = tmp_path / "test.json"
        
        success = CLIExporter.export_to_json(data, str(file_path))
        assert success == True
        assert file_path.exists()
        
        # Verify content
        with open(file_path, 'r') as f:
            loaded_data = json.load(f)
        assert loaded_data == data
    
    def test_export_to_csv(self, tmp_path):
        """Test CSV export"""
        data = [
            {'symbol': 'BTC/USDT', 'price': 42000, 'volume': 100},
            {'symbol': 'ETH/USDT', 'price': 3000, 'volume': 200}
        ]
        file_path = tmp_path / "test.csv"
        
        success = CLIExporter.export_to_csv(data, str(file_path))
        assert success == True
        assert file_path.exists()
    
    def test_export_backtest_report(self, tmp_path):
        """Test backtest report export"""
        results = {
            'strategy_name': 'Test Strategy',
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'initial_balance': 10000,
            'final_balance': 11500,
            'total_return_pct': 15.0,
            'total_trades': 25,
            'win_rate': 68.0,
            'sharpe_ratio': 1.8,
            'max_drawdown': -5.2,
            'trades_log': [
                {
                    'timestamp': '2024-01-01 10:00:00',
                    'side': 'buy',
                    'amount': 0.01,
                    'symbol': 'BTC/USDT',
                    'price': 42000
                }
            ]
        }
        file_path = tmp_path / "backtest_report.txt"
        
        success = CLIExporter.export_backtest_report(results, str(file_path))
        assert success == True
        assert file_path.exists()
        
        # Verify content
        content = file_path.read_text()
        assert 'Test Strategy' in content
        assert 'BTC/USDT' in content
        assert '15.00%' in content

class TestCLIIntegration:
    """Integration tests for CLI components"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies"""
        with patch('src.interfaces.cli.cli_main.ConfigManager') as mock_config, \
             patch('src.interfaces.cli.cli_main.Logger') as mock_logger, \
             patch('src.interfaces.cli.cli_main.RepositoryManager') as mock_repo, \
             patch('src.interfaces.cli.cli_main.APIClientManager') as mock_api:
            
            mock_config.return_value.get_all_config.return_value = {
                'trading': {'mode': 'paper'},
                'risk': {'max_trades': 10}
            }
            
            yield {
                'config': mock_config,
                'logger': mock_logger,
                'repository': mock_repo,
                'api': mock_api
            }
    
    def test_cli_initialization(self, mock_dependencies):
        """Test CLI initialization with mocked dependencies"""
        cli_instance = TradingBotCLI()
        assert cli_instance.config is not None
        assert cli_instance.logger is not None
        assert cli_instance.repository is not None
        assert cli_instance.api_clients is not None
    
    @patch('src.interfaces.cli.cli_main.cli_instance')
    def test_command_integration(self, mock_cli, mock_dependencies):
        """Test command integration with mocked CLI instance"""
        runner = CliRunner()
        
        # Mock initialization
        mock_cli.initialize = AsyncMock()
        mock_cli.config.get_all_config.return_value = {'test': 'config'}
        
        # Test config show command
        result = runner.invoke(cli, ['config', 'show'])
        assert result.exit_code == 0

# Async test utilities
def run_async_test(async_func):
    """Helper to run async test functions"""
    return asyncio.run(async_func())

@pytest.mark.asyncio
class TestAsyncCLIOperations:
    """Test async CLI operations"""
    
    async def test_cli_initialize(self):
        """Test async CLI initialization"""
        with patch('src.interfaces.cli.cli_main.ConfigManager'), \
             patch('src.interfaces.cli.cli_main.Logger'), \
             patch('src.interfaces.cli.cli_main.RepositoryManager') as mock_repo, \
             patch('src.interfaces.cli.cli_main.APIClientManager') as mock_api:
            
            mock_repo.return_value.initialize = AsyncMock()
            mock_api.return_value.initialize = AsyncMock()
            
            cli_instance = TradingBotCLI()
            await cli_instance.initialize()
            
            mock_repo.return_value.initialize.assert_called_once()
            mock_api.return_value.initialize.assert_called_once()

if __name__ == '__main__':
    pytest.main([__file__])

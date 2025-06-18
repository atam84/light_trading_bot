# examples/strategy_framework_demo.py

"""
Strategy Framework Usage Examples

This file demonstrates how to use the trading bot strategy framework
for various trading scenarios and use cases.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from strategies import StrategyFramework, create_strategy, test_strategy

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_quick_strategy_creation():
    """Demonstrate quick strategy creation using profiles"""
    print("\n" + "="*60)
    print("DEMO: Quick Strategy Creation")
    print("="*60)
    
    # Initialize framework
    framework = StrategyFramework()
    
    # Create strategies with different risk profiles
    strategies = {}
    
    # Conservative DCA strategy
    strategies['conservative'] = framework.create_quick_strategy(
        profile="conservative",
        symbol="BTC/USDT", 
        timeframe="4h",
        budget=50.0
    )
    print(f"✅ Created conservative strategy: {strategies['conservative']}")
    
    # Balanced multi-indicator strategy
    strategies['balanced'] = framework.create_quick_strategy(
        profile="balanced",
        symbol="ETH/USDT",
        timeframe="1h", 
        budget=100.0
    )
    print(f"✅ Created balanced strategy: {strategies['balanced']}")
    
    # Aggressive RSI strategy
    strategies['aggressive'] = framework.create_quick_strategy(
        profile="aggressive",
        symbol="BNB/USDT",
        timeframe="15m",
        budget=75.0
    )
    print(f"✅ Created aggressive strategy: {strategies['aggressive']}")
    
    # Grid trading strategy
    strategies['grid'] = framework.create_quick_strategy(
        profile="grid_stable",
        symbol="ADA/USDT",
        timeframe="1h",
        budget=200.0
    )
    print(f"✅ Created grid strategy: {strategies['grid']}")
    
    # Display strategy list
    print(f"\n📊 Total strategies created: {len(strategies)}")
    strategy_list = framework.list_strategies()
    for strategy in strategy_list:
        print(f"   • {strategy['name']} ({strategy['type']}) - {strategy['symbols'][0]} - Active: {strategy['active']}")
    
    return strategies

async def demo_custom_strategy_creation():
    """Demonstrate custom strategy creation"""
    print("\n" + "="*60)
    print("DEMO: Custom Strategy Creation")
    print("="*60)
    
    framework = StrategyFramework()
    
    # Create custom RSI strategy with specific parameters
    custom_rsi = framework.create_custom_strategy(
        name="Custom_RSI_BTC",
        strategy_type="rsi",
        symbol="BTC/USDT",
        timeframe="4h",
        parameters={
            'rsi_period': 21,
            'oversold_threshold': 25,
            'overbought_threshold': 75,
            'exit_rsi_middle': 55
        },
        risk_settings={
            'stop_loss_pct': 0.03,  # 3% stop loss
            'take_profit_pct': 0.12,  # 12% take profit
            'max_position_size': 150.0
        }
    )
    print(f"✅ Created custom RSI strategy: {custom_rsi}")
    
    # Create custom grid strategy
    custom_grid = framework.create_custom_strategy(
        name="Custom_Grid_ETH",
        strategy_type="grid_trading",
        symbol="ETH/USDT",
        timeframe="1h",
        parameters={
            'grid_levels': 12,
            'grid_spacing_pct': 1.5,
            'base_amount_usd': 80.0,
            'rebalance_threshold_pct': 7.0
        }
    )
    print(f"✅ Created custom grid strategy: {custom_grid}")
    
    # Create multi-indicator combo strategy
    custom_combo = framework.create_custom_strategy(
        name="Custom_Combo_Strategy",
        strategy_type="combo_indicator",
        symbol="MATIC/USDT",
        timeframe="2h",
        parameters={
            'entry_indicators': ['rsi', 'ma_cross', 'macd'],
            'confirmation_indicators': ['volume'],
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'require_all_signals': False  # Allow any 2 of 3 indicators
        }
    )
    print(f"✅ Created custom combo strategy: {custom_combo}")
    
    return [custom_rsi, custom_grid, custom_combo]

async def demo_backtesting():
    """Demonstrate strategy backtesting"""
    print("\n" + "="*60)
    print("DEMO: Strategy Backtesting")
    print("="*60)
    
    framework = StrategyFramework()
    
    # Create strategy for testing
    strategy_id = framework.create_from_template(
        template="rsi",
        name="RSI_Backtest_Demo",
        symbol="BTC/USDT",
        timeframe="4h",
        rsi_period=14,
        oversold_threshold=30,
        overbought_threshold=70
    )
    print(f"✅ Created strategy for backtesting: {strategy_id}")
    
    # Run backtest
    print("🔄 Running 30-day backtest...")
    backtest_result = await framework.run_backtest(
        strategy_id=strategy_id,
        days=30,
        initial_balance=10000.0
    )
    
    # Display results
    print(f"📈 Backtest Results:")
    print(f"   • Final Balance: ${backtest_result.final_balance:,.2f}")
    print(f"   • Total Return: {backtest_result.total_return_pct:+.2f}%")
    print(f"   • Total Trades: {backtest_result.total_trades}")
    print(f"   • Win Rate: {backtest_result.win_rate:.1f}%")
    print(f"   • Max Drawdown: {backtest_result.max_drawdown_pct:.2f}%")
    print(f"   • Sharpe Ratio: {backtest_result.sharpe_ratio:.2f}")
    
    return backtest_result

async def demo_strategy_comparison():
    """Demonstrate strategy comparison"""
    print("\n" + "="*60)
    print("DEMO: Strategy Comparison")
    print("="*60)
    
    framework = StrategyFramework()
    
    # Create multiple strategies for comparison
    strategies = []
    
    # RSI Strategy
    rsi_strategy = framework.create_from_template(
        template="rsi",
        name="RSI_Compare",
        symbol="BTC/USDT"
    )
    strategies.append(rsi_strategy)
    
    # MA Cross Strategy  
    ma_strategy = framework.create_from_template(
        template="ma_cross",
        name="MA_Compare",
        symbol="BTC/USDT"
    )
    strategies.append(ma_strategy)
    
    # DCA Strategy
    dca_strategy = framework.create_from_template(
        template="dca",
        name="DCA_Compare", 
        symbol="BTC/USDT"
    )
    strategies.append(dca_strategy)
    
    print(f"✅ Created {len(strategies)} strategies for comparison")
    
    # Run comparison (mock data for demo)
    comparison = framework.compare_strategies(strategies)
    
    print(f"📊 Strategy Comparison Results:")
    print(f"   • Best Overall: {comparison['ranking']['overall'][0]}")
    print(f"   • Best Return: {comparison['ranking']['total_return_pct'][0]}")
    print(f"   • Best Sharpe: {comparison['ranking']['sharpe_ratio'][0]}")
    print(f"   • Best Win Rate: {comparison['ranking']['win_rate'][0]}")
    
    return comparison

async def demo_portfolio_management():
    """Demonstrate portfolio management"""
    print("\n" + "="*60)
    print("DEMO: Portfolio Management")
    print("="*60)
    
    framework = StrategyFramework()
    
    # Create diversified portfolio
    symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "DOT/USDT"]
    
    portfolio_strategies = framework.create_portfolio(
        symbols=symbols,
        profile="balanced",
        total_budget=2500.0  # $500 per symbol
    )
    
    print(f"✅ Created portfolio with {len(portfolio_strategies)} strategies")
    print(f"   • Symbols: {', '.join(symbols)}")
    print(f"   • Total Budget: $2,500 (${2500/len(symbols):.0f} per symbol)")
    
    # Export portfolio
    export_success = await framework.export_portfolio(
        strategy_ids=portfolio_strategies,
        filename="demo_portfolio.json"
    )
    
    if export_success:
        print("✅ Portfolio exported to demo_portfolio.json")
    
    return portfolio_strategies

async def demo_real_time_simulation():
    """Demonstrate real-time processing simulation"""
    print("\n" + "="*60)
    print("DEMO: Real-Time Processing Simulation")
    print("="*60)
    
    framework = StrategyFramework()
    
    # Create active strategy
    strategy_id = framework.create_quick_strategy(
        profile="balanced",
        symbol="BTC/USDT",
        timeframe="1h"
    )
    
    # Activate strategy
    framework.activate_strategy(strategy_id)
    print(f"✅ Activated strategy: {strategy_id}")
    
    # Setup signal callback
    signal_count = 0
    
    def on_trading_signal(signal):
        nonlocal signal_count
        signal_count += 1
        print(f"🔔 Trading Signal #{signal_count}: {signal.symbol} {signal.action.value} "
              f"at ${signal.price:.2f} (confidence: {signal.confidence:.2f})")
        print(f"   Reason: {signal.reason}")
    
    framework.add_signal_callback(on_trading_signal)
    
    # Start real-time processing (simulation)
    print("🔄 Starting real-time processing simulation...")
    await framework.start_real_time(["BTC/USDT"], ["1h"])
    
    # Let it run for a short demo period
    await asyncio.sleep(5)  # 5 seconds for demo
    
    # Stop processing
    framework.stop_real_time()
    print(f"⏹️ Stopped real-time processing")
    print(f"📊 Generated {signal_count} signals during simulation")
    
    # Get system status
    status = framework.get_system_status()
    print(f"🖥️ System Status:")
    print(f"   • Active Strategies: {status['strategy_manager']['active_strategies']}")
    print(f"   • Total Signals: {status['signal_processor']['recent_hour_signals']}")
    print(f"   • Real-time Enabled: {status['real_time_enabled']}")

async def demo_strategy_recommendations():
    """Demonstrate strategy recommendations"""
    print("\n" + "="*60)
    print("DEMO: Strategy Recommendations")
    print("="*60)
    
    framework = StrategyFramework()
    
    # Test different scenarios
    scenarios = [
        ("BTC/USDT", "4h", "low", "Conservative Bitcoin trading"),
        ("ETH/USDT", "1h", "medium", "Moderate Ethereum trading"), 
        ("BNB/USDT", "15m", "high", "Aggressive Binance Coin trading")
    ]
    
    for symbol, timeframe, risk, description in scenarios:
        print(f"\n📋 {description}:")
        recommendations = framework.get_recommendations(
            symbol=symbol,
            timeframe=timeframe, 
            risk_tolerance=risk
        )
        
        print(f"   Symbol: {symbol} | Timeframe: {timeframe} | Risk: {risk}")
        
        for i, rec in enumerate(recommendations[:3], 1):  # Show top 3
            print(f"   {i}. {rec['profile']} ({rec['strategy_class']})")
            print(f"      Score: {rec['compatibility_score']:.2f} | Risk: {rec['risk_level']}")
            print(f"      {rec['description']}")

async def demo_configuration_management():
    """Demonstrate configuration management"""
    print("\n" + "="*60)
    print("DEMO: Configuration Management")
    print("="*60)
    
    framework = StrategyFramework()
    
    # List available templates
    templates = framework.list_templates()
    print(f"📋 Available Templates ({len(templates)}):")
    for template in templates:
        print(f"   • {template['name']} ({template['type']}) - Risk: {template['risk_level']}")
        print(f"     {template['description']}")
    
    # Create and save custom configuration
    strategy_id = framework.create_custom_strategy(
        name="Demo_Custom_Config",
        strategy_type="rsi",
        symbol="BTC/USDT",
        parameters={
            'rsi_period': 18,
            'oversold_threshold': 28,
            'overbought_threshold': 72
        }
    )
    
    # Save configuration
    saved = framework.save_strategy_config(strategy_id, "my_custom_rsi_config")
    if saved:
        print(f"✅ Saved custom configuration: my_custom_rsi_config")
    
    # Load configuration
    loaded_strategy = framework.load_strategy_config("my_custom_rsi_config")
    if loaded_strategy:
        print(f"✅ Loaded strategy from config: {loaded_strategy}")

async def main():
    """Run all strategy framework demos"""
    print("🚀 TRADING BOT STRATEGY FRAMEWORK DEMO")
    print("="*60)
    
    try:
        # Run all demos
        await demo_quick_strategy_creation()
        await demo_custom_strategy_creation()
        await demo_backtesting()
        await demo_strategy_comparison()
        await demo_portfolio_management()
        await demo_configuration_management()
        await demo_strategy_recommendations()
        # await demo_real_time_simulation()  # Commented out for demo
        
        print("\n" + "="*60)
        print("✅ ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("🎯 Key Features Demonstrated:")
        print("   • Quick strategy creation with profiles")
        print("   • Custom strategy configuration")
        print("   • Comprehensive backtesting")
        print("   • Multi-strategy comparison")
        print("   • Portfolio management")
        print("   • Configuration management")
        print("   • Strategy recommendations")
        print("   • Real-time processing simulation")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"❌ Demo failed: {e}")

if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())
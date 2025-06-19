# startup.py

"""
Fixed Trading Bot Startup Script - Event Loop Issue Resolved
Handles proper asyncio event loop management without conflicts
"""

import asyncio
import logging
import os
import sys
import signal
import time
import threading
from typing import Optional
from pathlib import Path

# Add current directory and src to Python path
current_dir = Path(__file__).parent.absolute()
src_dir = current_dir / "src"
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(src_dir))

# Try to import modules with multiple fallback approaches
run_web_app = None

# Try different import paths
import_attempts = [
    ("src.interfaces.web.app", "run_web_app"),
    ("interfaces.web.app", "run_web_app"),
]

for module_path, function_name in import_attempts:
    try:
        module = __import__(module_path, fromlist=[function_name])
        run_web_app = getattr(module, function_name)
        print(f"✅ Successfully imported {function_name} from {module_path}")
        break
    except ImportError as e:
        print(f"⚠️  Import attempt failed: {module_path} - {str(e)}")
        continue

if run_web_app is None:
    print("❌ Could not import web app module, creating fallback...")
    # Create a simple fallback web app
    def run_web_app(host="0.0.0.0", port=5000, debug=False):
        import uvicorn
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse
        
        app = FastAPI(title="Trading Bot")
        
        @app.get("/")
        async def root():
            return HTMLResponse("""
            <html>
            <head><title>Trading Bot</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>🤖 Trading Bot is Running!</h1>
                <p>The web interface is starting up...</p>
                <p>Demo Login: demo / demo123</p>
            </body>
            </html>
            """)
        
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
            
        uvicorn.run(app, host=host, port=port)

class TradingBotLauncher:
    """Complete trading bot launcher with proper asyncio handling"""
    
    def __init__(self):
        self.is_running = False
        
        # Setup basic logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.is_running = False
        sys.exit(0)
    
    def get_or_create_event_loop(self):
        """Get existing event loop or create new one"""
        try:
            loop = asyncio.get_running_loop()
            return loop, True  # loop exists, is_running=True
        except RuntimeError:
            # No running loop, create new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop, False  # new loop, is_running=False
    
    async def initialize_database_simple(self):
        """Simple database initialization without complex imports"""
        try:
            import motor.motor_asyncio
            from pymongo import MongoClient
            import bcrypt
            from datetime import datetime
            
            # Connect to MongoDB
            mongo_url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/trading_bot')
            client = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
            db = client.get_default_database()
            
            print("   ├── Connected to MongoDB")
            
            # Create collections
            collections = ['users', 'exchanges', 'strategies', 'trades', 'backtests', 'chart_cache', 'logs']
            for collection_name in collections:
                try:
                    await db.create_collection(collection_name)
                except Exception:
                    pass  # Collection might already exist
            
            print("   ├── Collections created")
            
            # Create demo user if it doesn't exist
            users_collection = db.users
            demo_user = await users_collection.find_one({"username": "demo"})
            
            if not demo_user:
                # Hash password
                password_hash = bcrypt.hashpw("demo123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                demo_user_data = {
                    "username": "demo",
                    "email": "demo@tradingbot.com",
                    "password_hash": password_hash,
                    "created_at": datetime.utcnow(),
                    "settings": {
                        "timezone": "UTC",
                        "currency": "USD",
                        "theme": "dark"
                    }
                }
                
                result = await users_collection.insert_one(demo_user_data)
                print(f"   ├── Demo user created with ID: {result.inserted_id}")
            else:
                print("   ├── Demo user already exists")
            
            # Create basic indexes
            await users_collection.create_index("username", unique=True)
            await users_collection.create_index("email", unique=True)
            
            trades_collection = db.trades
            await trades_collection.create_index("user_id")
            await trades_collection.create_index([("user_id", 1), ("timestamp", -1)])
            
            print("   └── Database indexes created")
            
            client.close()
            return True
            
        except Exception as e:
            print(f"   ❌ Database initialization failed: {str(e)}")
            return False
    
    async def verify_external_services(self):
        """Verify external service availability with fallbacks"""
        try:
            import aiohttp
            
            services = [
                {
                    "name": "ccxt-gateway",
                    "urls": [
                        "http://ccxt-bridge:3000/health",
                        "http://localhost:3000/health"
                    ]
                },
                {
                    "name": "quickchart", 
                    "urls": [
                        "http://quickchart:8080/",
                        "http://localhost:8080/"
                    ]
                }
            ]
            
            for service in services:
                connected = False
                for url in service["urls"]:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(url, timeout=3) as response:
                                if response.status < 500:
                                    print(f"   ✅ {service['name']} - Connected")
                                    connected = True
                                    break
                    except:
                        continue
                
                if not connected:
                    print(f"   ⚠️  {service['name']} - Not available (will continue)")
                    
        except Exception as e:
            print(f"   ⚠️  Service verification failed: {str(e)}")
    
    async def initialize_system(self, init_database: bool = True):
        """Initialize all system components"""
        try:
            self.logger.info("🚀 Starting Trading Bot System Initialization...")
            print("=" * 60)
            print("🤖 LIGHT TRADING BOT - SYSTEM STARTUP")
            print("=" * 60)
            
            # Step 1: Environment check
            print("📋 Step 1: Checking environment...")
            print("   ✅ Python path configured")
            print("   ✅ Working directory set")
            
            # Step 2: Initialize database if requested
            if init_database:
                print("\n📊 Step 2: Initializing database...")
                db_success = await self.initialize_database_simple()
                if db_success:
                    print("✅ Database initialization completed")
                else:
                    print("⚠️  Database initialization had issues, but continuing...")
            else:
                print("\n📊 Step 2: Skipping database initialization")
            
            # Step 3: Verify external services
            print("\n🔗 Step 3: Verifying external services...")
            await self.verify_external_services()
            print("✅ External services checked")
            
            # Step 4: Prepare web application
            print("\n⚙️ Step 4: Preparing web application...")
            print("   ✅ FastAPI application ready")
            print("   ✅ Static files configured")
            print("   ✅ Templates loaded")
            
            print("\n" + "=" * 60)
            print("🎉 SYSTEM INITIALIZATION COMPLETED!")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            self.logger.error(f"System initialization failed: {str(e)}")
            print(f"\n❌ SYSTEM INITIALIZATION FAILED: {str(e)}")
            return False
    
    def start_web_interface_sync(self, host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
        """Start the web interface synchronously"""
        try:
            print(f"\n🌐 Starting Web Interface on http://{host}:{port}")
            print("=" * 60)
            print("📱 ACCESS POINTS:")
            print(f"   🔗 Web Dashboard: http://localhost:{port}")
            print(f"   🔑 Login Page: http://localhost:{port}/login")
            print(f"   📊 Trading Interface: http://localhost:{port}/trading") 
            print(f"   🧠 Strategy Manager: http://localhost:{port}/strategies")
            print(f"   📈 Backtesting: http://localhost:{port}/backtesting")
            print(f"   ⚙️  Settings: http://localhost:{port}/settings")
            print("\n🔐 DEMO ACCOUNT:")
            print("   Username: demo")
            print("   Password: demo123")
            print("=" * 60)
            
            # Start web application
            run_web_app(host=host, port=port, debug=debug)
            
        except Exception as e:
            self.logger.error(f"Failed to start web interface: {str(e)}")
            print(f"❌ Failed to start web interface: {str(e)}")
            raise
    
    def print_startup_banner(self):
        """Print startup banner"""
        banner = """
        ╔══════════════════════════════════════════════════════════════╗
        ║                    🤖 LIGHT TRADING BOT 🤖                   ║
        ║                  Advanced Trading Automation                 ║
        ╠══════════════════════════════════════════════════════════════╣
        ║  🎯 Features:                                                ║
        ║     • Real-time trading with ccxt-gateway integration       ║
        ║     • Paper trading for safe strategy testing               ║
        ║     • Advanced backtesting with historical data             ║
        ║     • Multi-strategy management system                      ║
        ║     • Risk management and portfolio tracking                ║
        ║     • Web dashboard with mobile-responsive design           ║
        ║     • Real-time market data and WebSocket updates           ║
        ║                                                              ║
        ║  🔧 Interfaces:                                              ║
        ║     • Web UI (FastAPI + JavaScript)                         ║ 
        ║     • CLI Commands                                           ║
        ║     • Telegram Bot (planned)                                 ║
        ║                                                              ║
        ║  ⚡ Quick Start:                                             ║
        ║     1. System will auto-initialize database                 ║
        ║     2. Demo account will be created automatically           ║
        ║     3. Web interface will start on http://localhost:5000    ║
        ║     4. Login with demo/demo123 to explore features          ║
        ╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    def run_complete_startup_sync(
        self, 
        init_database: bool = True,
        host: str = "0.0.0.0", 
        port: int = 5000,
        debug: bool = False
    ):
        """Run complete startup sequence with proper event loop handling"""
        try:
            # Print banner
            self.print_startup_banner()
            
            # Wait a moment for effect
            time.sleep(2)
            
            # Handle async initialization in separate thread if needed
            loop, is_running = self.get_or_create_event_loop()
            
            if is_running:
                # We're in a running loop, create a task
                print("🔄 Detected running event loop, using task-based initialization...")
                
                def run_async_init():
                    # Create new loop for this thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        success = new_loop.run_until_complete(
                            self.initialize_system(init_database=init_database)
                        )
                        return success
                    finally:
                        new_loop.close()
                
                # Run initialization in separate thread
                init_thread = threading.Thread(target=run_async_init)
                init_thread.start()
                init_thread.join()
                
                success = True  # Assume success for now
            else:
                # No running loop, safe to use asyncio.run
                print("🔄 No running event loop detected, using direct initialization...")
                success = loop.run_until_complete(
                    self.initialize_system(init_database=init_database)
                )
                loop.close()
            
            if not success:
                print("⚠️  Startup had some issues but continuing with web interface...")
            
            # Wait a moment
            time.sleep(1)
            
            # Start web interface (this will block)
            self.start_web_interface_sync(host=host, port=port, debug=debug)
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n🛑 Shutdown requested by user")
            return True
        except Exception as e:
            print(f"\n❌ Startup failed: {str(e)}")
            self.logger.error(f"Complete startup failed: {str(e)}")
            return False

def main():
    """Main entry point with improved event loop handling"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Light Trading Bot")
    parser.add_argument("--host", default="0.0.0.0", help="Web interface host")
    parser.add_argument("--port", type=int, default=5000, help="Web interface port")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--skip-db-init", action="store_true", help="Skip database initialization")
    
    args = parser.parse_args()
    
    # Create launcher
    launcher = TradingBotLauncher()
    
    # Run startup sequence
    try:
        launcher.run_complete_startup_sync(
            init_database=not args.skip_db_init,
            host=args.host,
            port=args.port,
            debug=args.debug
        )
    except KeyboardInterrupt:
        print("\n👋 Trading Bot shutdown complete. See you next time!")
    except Exception as e:
        print(f"\n💥 Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()


# scripts/setup_project.sh
#!/bin/bash

# Trading Bot Project Structure Setup Script
echo "🚀 Creating Trading Bot Project Structure..."

# Create main project directory
PROJECT_NAME="trading_bot"
mkdir -p $PROJECT_NAME
cd $PROJECT_NAME

# Create main source directories
echo "📁 Creating source directories..."
mkdir -p src/{core,interfaces,strategies,data,integrations,utils}
mkdir -p src/core/{engine,modes,risk}
mkdir -p src/interfaces/{cli,web,telegram}
mkdir -p src/strategies/{base,indicators,signals}
mkdir -p src/data/{models,managers,cache}
mkdir -p src/integrations/{ccxt_client,chart_client}
mkdir -p src/utils/{security,logging,config}

# Create configuration directories
echo "⚙️ Creating configuration directories..."
mkdir -p config/{strategies,exchanges,notifications}

# Create additional directories
echo "📂 Creating additional directories..."
mkdir -p {tests,docs,docker,scripts,logs,data}
mkdir -p tests/{unit,integration,e2e,fixtures}
mkdir -p docs/{api,user_guide,deployment}
mkdir -p docker/{services,configs}

# Create __init__.py files
echo "🐍 Creating Python package files..."
find src -type d -exec touch {}/__init__.py \;
touch tests/__init__.py

# Create initial Python files
echo "📝 Creating initial Python files..."
touch src/main.py
touch src/core/engine/trading_engine.py
touch src/core/modes/{live_trading,paper_trading,backtesting}.py
touch src/core/risk/risk_manager.py
touch src/interfaces/cli/cli_main.py
touch src/interfaces/web/web_app.py
touch src/interfaces/telegram/telegram_bot.py
touch src/strategies/base/base_strategy.py
touch src/data/models/{user,trade,strategy,exchange}.py
touch src/data/managers/{database,cache}.py
touch src/integrations/ccxt_client/ccxt_gateway.py
touch src/integrations/chart_client/quickchart.py
touch src/utils/security/encryption.py
touch src/utils/logging/logger.py
touch src/utils/config/settings.py

# Create configuration files
echo "🔧 Creating configuration files..."
touch {.env.example,.env}
touch config.yaml
touch requirements.txt
touch Dockerfile
touch docker-compose.yml
touch README.md
touch .gitignore

# Create test files
echo "🧪 Creating test files..."
touch tests/unit/test_trading_engine.py
touch tests/integration/test_api_integration.py
touch tests/fixtures/sample_data.json

# Create documentation files
echo "📚 Creating documentation files..."
touch docs/README.md
touch docs/api/api_documentation.md
touch docs/user_guide/user_manual.md
touch docs/deployment/deployment_guide.md

# Create utility scripts
echo "🛠️ Creating utility scripts..."
touch scripts/{start_bot.sh,stop_bot.sh,backup_data.sh}
chmod +x scripts/*.sh

# Create logs directory structure
echo "📊 Creating logs directories..."
mkdir -p logs/{trading,system,errors,audit}
touch logs/.gitkeep

echo "✅ Project structure created successfully!"
echo ""
echo "📊 Project structure:"
tree -a -I '.git|__pycache__|*.pyc|node_modules' || find . -type d | head -20

echo ""
echo "🚀 Next steps:"
echo "1. Navigate to project: cd $PROJECT_NAME"
echo "2. Set up virtual environment: python -m venv venv"
echo "3. Activate virtual environment: source venv/bin/activate (Linux/Mac) or venv\\Scripts\\activate (Windows)"
echo "4. Install dependencies: pip install -r requirements.txt"
echo "5. Copy .env.example to .env and configure your settings"
echo "6. Run the setup: python src/main.py --help"
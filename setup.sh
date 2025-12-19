#!/bin/bash
# DataPilot Setup Script

set -e

echo "=========================================="
echo "DataPilot Environment Setup"
echo "=========================================="

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if database exists
echo ""
echo "Checking database..."
DB_PATH="data/sample.db"
if [ ! -f "$DB_PATH" ]; then
    echo "Database not found. Initializing database..."
    python scripts/init_database.py
    echo "✓ Database initialized"
else
    echo "✓ Database already exists: $DB_PATH"
    echo "  (Run 'python scripts/init_database.py --reset' to recreate)"
fi

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Set up Ollama (see OLLAMA_SETUP.md):"
echo "   - Install: brew install ollama"
echo "   - Start: ollama serve"
echo "   - Pull model: ollama pull mistral"
echo ""
echo "2. Configure bot token:"
echo "   - Create .env file: echo 'TELEGRAM_BOT_TOKEN=your_token' > .env"
echo "   - Or export: export TELEGRAM_BOT_TOKEN='your_token'"
echo ""
echo "3. Run the bot:"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "To activate the environment manually:"
echo "  source venv/bin/activate"
echo ""
echo "To deactivate:"
echo "  deactivate"
echo ""


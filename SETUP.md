# Setup Guide

Quick setup instructions for DataPilot.

## Quick Start

### Option 1: Use Setup Script (Recommended)

```bash
./setup.sh
```

This will:
- Create virtual environment (if needed)
- Activate it
- Upgrade pip
- Install all dependencies

### Option 2: Manual Setup

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   ```

2. **Activate virtual environment:**
   
   **macOS/Linux:**
   ```bash
   source venv/bin/activate
   ```
   
   **Windows:**
   ```bash
   venv\Scripts\activate
   ```

3. **Upgrade pip:**
   ```bash
   pip install --upgrade pip
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Verify Installation

Check that everything is installed:

```bash
python -c "import langchain; import telegram; import sqlite3; print('✓ All packages installed')"
```

## Ollama Setup

DataPilot requires Ollama to run LLM models locally. Follow these steps:

### What is Ollama?

Ollama is a tool that makes it easy to run large language models locally. It handles model downloads, management, and provides a simple API.

### Installation

#### macOS

```bash
# Install using Homebrew
brew install ollama

# Or download from https://ollama.ai/download
```

#### Linux

```bash
# Install using curl
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Windows

Download the installer from https://ollama.ai/download

### Start Ollama

After installation, start the Ollama service:

```bash
ollama serve
```

This will start the Ollama API server on `http://localhost:11434` (default port).

### Download Models

DataPilot works with various open-source models. Recommended models:

#### For Intent Clarification & Insights (General Purpose)

```bash
# Mistral 7B (Recommended - good balance)
ollama pull mistral

# LLaMA 3 8B (Alternative)
ollama pull llama3

# Qwen 2.5 7B (Good alternative)
ollama pull qwen2.5:7b
```

#### For SQL Generation (Code-Focused)

```bash
# CodeLlama 7B (Best for SQL)
ollama pull codellama:7b

# DeepSeek Coder (Alternative)
ollama pull deepseek-coder:6.7b
```

#### Unified Model (Recommended for POC)

For Phase 1, use a single model for all agents:

```bash
# Mistral is a good general-purpose model
ollama pull mistral
```

Then update `src/config/config.yaml`:
```yaml
llm:
  model_name: "mistral"  # Use the same model for all agents
```

### Verify Installation

Test that Ollama is working:

```bash
# Test with a simple query
ollama run mistral "Hello, how are you?"
```

Or test the API:

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "Why is the sky blue?",
  "stream": false
}'
```

### Configuration

Update `src/config/config.yaml`:

```yaml
llm:
  provider: "ollama"
  base_url: "http://localhost:11434"  # Default Ollama URL (optional)
  model_name: "mistral"  # Change to your preferred model
  temperature: 0.7
  max_tokens: 2048
  timeout: 60
```

**Note:** `base_url` is optional. If not specified, LangChain will use the default `http://localhost:11434`.

### Model Recommendations

| Use Case | Recommended Model | Command |
|----------|------------------|---------|
| General purpose (POC) | Mistral 7B | `ollama pull mistral` |
| SQL generation | CodeLlama 7B | `ollama pull codellama:7b` |
| Best quality | LLaMA 3 8B | `ollama pull llama3` |
| Smaller/faster | Qwen 2.5 3B | `ollama pull qwen2.5:3b` |

### Ollama Troubleshooting

#### Ollama not starting

```bash
# Check if Ollama is running
ps aux | grep ollama

# Restart Ollama
ollama serve
```

#### Model not found

```bash
# List available models
ollama list

# Pull the model again
ollama pull <model-name>
```

#### Connection refused

- Make sure Ollama is running: `ollama serve`
- Check the port: Default is 11434
- Verify URL in config: `base_url: "http://localhost:11434"` (optional)

#### Out of memory

- Use smaller models (3B or 7B instead of 13B+)
- Close other applications
- Consider using quantized models (they're automatically quantized by Ollama)

## Next Steps

1. **Set up Ollama** (see above)
   - Install Ollama
   - Start Ollama: `ollama serve`
   - Pull a model: `ollama pull mistral` (or your preferred model)

2. **Configure bot token:**
   - Create `.env` file in project root:
     ```bash
     echo "TELEGRAM_BOT_TOKEN=your_token_here" > .env
     ```
   - Or set environment variable:
     ```bash
     export TELEGRAM_BOT_TOKEN="your_token_here"
     ```

3. **Initialize database (REQUIRED):**
   ```bash
   # Create the database with sample data
   python scripts/init_database.py
   ```
   
   This will:
   - Create `data/sample.db` (SQLite database)
   - Create all tables (categories, users, products, orders)
   - Insert sample data (50 users, 12 products, 150+ orders)
   
   **Expected output:**
   ```
   ============================================================
   DataPilot Database Initialization (SQLite)
   ============================================================
   Creating database: data/sample.db
   
   Creating tables...
   ✓ Created table: categories
   ✓ Created table: users
   ✓ Created table: products
   ✓ Created table: orders
   
   Inserting sample data...
   ✓ Inserted 5 categories
   ✓ Inserted 12 products
   ✓ Inserted 50 users
   ✓ Inserted 156 orders
   ...
   ```

4. **Run the bot:**
   ```bash
   python main.py
   ```

## Testing the Bot

### Basic Commands

1. **Start the bot:**
   ```
   /start
   ```
   Should show welcome message.

2. **Get help:**
   ```
   /help
   ```

### Example Questions to Ask

Based on the sample data, try these questions:

#### Simple Questions:
```
What's our total revenue?
```

```
How many orders do we have?
```

```
Show me the average order value
```

#### Questions with Dimensions:
```
What's our total revenue by country?
```

```
Show me sales by product category
```

```
What are our top 5 products by revenue?
```

#### Time-based Questions:
```
What's our revenue for last month?
```

```
Show me orders by month
```

#### Complex Questions:
```
What's our total revenue by country for the last 3 months?
```

```
Show me the breakdown of sales by category and country
```

### What Happens When You Ask a Question?

1. **Intent Clarification** - Bot extracts your question into structured format
2. **Schema Selection** - Bot finds relevant tables and columns
3. **SQL Generation** - Bot generates SQL query
4. **SQL Validation** - Bot checks query safety
5. **Your Approval** - Bot asks if you want to run the query
6. **Execution** - Bot runs query and shows results
7. **Insights** - Bot generates human-readable insights

### Sample Data Overview

The database contains:
- **5 categories**: Electronics, Clothing, Books, Home & Garden, Sports & Outdoors
- **12 products**: Laptop, Mouse, Smartphone, T-Shirt, Jeans, etc.
- **50 users**: From 10 different countries
- **150+ orders**: Distributed across last 6 months
- **Status distribution**: 85% completed, 10% pending, 5% cancelled

## Troubleshooting

### Virtual environment not activating

Make sure you're in the project directory:
```bash
cd /path/to/DataPilot
source venv/bin/activate
```

### Permission denied on setup.sh

```bash
chmod +x setup.sh
./setup.sh
```

### Python version issues

Requires Python 3.9+. Check version:
```bash
python3 --version
```

If you need a different Python version:
```bash
python3.11 -m venv venv  # Example for Python 3.11
```

### "Database not found" error
- Run: `python scripts/init_database.py`
- Make sure `data/sample.db` exists

### "TELEGRAM_BOT_TOKEN not found"
- Create `.env` file with: `TELEGRAM_BOT_TOKEN=your_token_here`
- Or set environment variable: `export TELEGRAM_BOT_TOKEN="your_token_here"`

### "Ollama connection error"
- Make sure Ollama is running: `ollama serve`
- Check if model is pulled: `ollama list`
- Verify model name in `src/config/config.yaml` matches your pulled model

### Bot doesn't respond
- Check logs in `logs/datapilot.log`
- Make sure bot token is correct
- Verify Ollama is accessible
- Check that database is initialized: `ls -la data/sample.db`


# DataPilot

AI Data Analyst Agent - Telegram Bot with Open-Source LLM and SQL-Aware Architecture

## Overview

DataPilot is a Telegram-based AI assistant that helps users query their data using natural language. It understands business questions, generates safe SQL queries, and provides human-readable insights.

## Features

- 🤖 **Natural Language Interface**: Ask questions in plain English
- 🔒 **SQL Safety**: Automatic validation and read-only enforcement
- 🧠 **Open-Source LLM**: Uses Ollama with Mistral, LLaMA, or CodeLLaMA models
- 📊 **Smart Insights**: Automatically generates insights from query results
- 🔄 **Human-in-the-Loop**: Review, modify, and approve SQL before execution
- ✏️ **SQL Editing**: Directly edit generated SQL queries
- 🛠️ **LangChain Integration**: Uses LangChain for LLM orchestration and SQL tools

## Architecture

See [DESIGN.md](DESIGN.md) for detailed architecture documentation.

### Key Components

- **Agent 1: Intent Clarifier** - Extracts and clarifies user intent using LangChain + Ollama
- **Agent 2: SQL Generator** - Generates SQL from structured intent using LangChain + Ollama
- **Agent 4: Insight Generator** - Creates human-readable insights using LangChain + Ollama
- **Schema Selector** - Discovers relevant tables and joins from metadata
- **SQL Validator** - Ensures query safety using sqlglot
- **SQL Executor** - Executes read-only queries using LangChain SQLDatabase tools
- **Result Reducer** - Prepares compact summaries for LLM processing

## Setup

### Prerequisites

- Python 3.9+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- **Ollama** installed and running (see [SETUP.md](SETUP.md#ollama-setup))
- At least one Ollama model pulled (e.g., `ollama pull mistral`)
- SQLite database (will be created automatically with sample data)

### Installation

1. **Clone and navigate to the project:**
```bash
cd DataPilot
```

2. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up Ollama:**
   - Install Ollama: See [SETUP.md](SETUP.md#ollama-setup) for detailed instructions
   - Start Ollama service: `ollama serve`
   - Pull a model: `ollama pull mistral` (or your preferred model)
   - Verify it works: `ollama run mistral "Hello"`

5. **Configure the bot:**
   - Create `.env` file in project root:
     ```bash
     echo "TELEGRAM_BOT_TOKEN=your_token_here" > .env
     ```
   - Or set environment variable:
     ```bash
     export TELEGRAM_BOT_TOKEN="your_bot_token_here"
     ```
   - Update `src/config/config.yaml` (optional):
     - Set `model_name` to your Ollama model (e.g., "mistral")
     - Adjust `base_url` only if Ollama is not on localhost:11434

6. **Initialize database:**
   ```bash
   # Create database with sample data
   python scripts/init_database.py
   
   # Or reset existing database
   python scripts/init_database.py --reset
   ```
   
   This will create `data/sample.db` (SQLite) with sample data matching your schema.
   - See example below for creating sample data

## Usage

### Start the Bot

```bash
python main.py
```

### Interact with the Bot

1. Open Telegram and find your bot
2. Send `/start` to begin
3. Ask questions like:
   - "What's our total revenue?"
   - "Show me sales by country"
   - "Compare this month to last month"

### Example Flow

```
User: What's our total revenue by country?

Bot: 🤔 Analyzing your question...
     ✅ Intent confirmed:
     • Metric: total_revenue
     • Dimensions: country
     • Time range: N/A
     
     [Confirm] [Modify] [Cancel]

User: [Clicks Confirm]

Bot: 🔧 Generating SQL query...
     ✅ SQL validated successfully!
     
     SELECT country, SUM(amount) AS revenue
     FROM orders
     JOIN users ON orders.user_id = users.user_id
     WHERE status = 'completed'
     GROUP BY country
     
     [▶️ Run query] [🧾 Show SQL only] [✏️ Modify SQL] [🔄 Modify intent] [❌ Cancel]

User: [Clicks Run query]

Bot: ⚙️ Executing query...
     🔍 Generating insights...
     
     ## Summary
     Total revenue by country shows strong performance...
```

## Project Structure

```
DataPilot/
├── src/
│   ├── agents/          # LLM agents (LangChain + Ollama)
│   │   ├── base_agent.py
│   │   ├── intent_clarifier.py
│   │   ├── sql_generator.py
│   │   └── insight_generator.py
│   ├── tools/           # Non-LLM tools
│   │   ├── schema_selector.py
│   │   ├── sql_validator.py
│   │   ├── sql_executor.py  # Uses LangChain SQLDatabase
│   │   └── result_reducer.py
│   ├── bot/             # Telegram bot
│   │   ├── telegram_bot.py
│   │   ├── states.py
│   │   ├── handlers.py
│   │   └── keyboards.py
│   ├── config/          # Configuration
│   │   └── config.yaml
│   ├── prompts.py       # Prompt loader (loads from prompts.yaml)
│   └── utils/           # Utilities
│       ├── logger.py
│       ├── db.py        # DatabaseManager (SQLite via LangChain)
│       └── state_store.py
├── metadata/            # Schema and metrics
│   ├── schema.json
│   └── metrics.yaml
├── data/                # Database files (SQLite)
│   └── sample.db        # Created by init_database.py
├── logs/                # Log files
├── scripts/             # Utility scripts
│   └── init_database.py # Database initialization (SQLite)
├── main.py              # Entry point
├── requirements.txt
├── setup.sh             # Automated setup script
├── SETUP.md             # Setup guide (includes Ollama setup)
├── DESIGN.md            # Design documentation
└── prompts.yaml         # All prompts in YAML format
```

## Configuration

Key configuration options in `src/config/config.yaml`:

- **LLM**: Ollama model name, temperature, max tokens, timeout, base_url (optional)
- **Database**: SQLite URI (`sqlite:///data/sample.db`), read-only mode, timeout
- **SQL Validator**: Safety rules and limits
- **Intent Clarifier**: Max clarification rounds, confidence threshold
- **Logging**: Level, format, file path

### Prompts

All prompts are stored in `src/prompts.yaml` for easy editing. The `src/prompts.py` module loads them automatically.

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
```

### Linting

```bash
flake8 src/
```

## Current Status

This is a **POC (Proof of Concept)** implementation. Current status:

✅ **Completed:**
- Project structure
- Configuration management (YAML-based)
- **Ollama + LangChain integration** (ChatOllama, SQLDatabase)
- **Intent clarification with structured output** (Pydantic)
- **SQL generation with LangChain** (prompt-based)
- **Insight generation with LangChain** (prompt-based)
- Telegram bot framework (state machine, handlers, keyboards)
- State management (SQLite-based)
- SQL validator (sqlglot-based, safety rules)
- Database connection manager (SQLite via LangChain SQLDatabase)
- Schema selector with join discovery
- **SQL editing feature** (users can modify generated SQL)
- **Empty result handling** (helpful error messages)
- **Prompt management** (YAML-based, easy to edit)
- **HTML message formatting** (reliable code display)

🚧 **In Progress:**
- Multi-hop join discovery (basic implementation done, needs enhancement)
- Error handling and retry logic
- Conversation context management

📋 **Planned:**
- Comprehensive testing
- Advanced result reduction
- Query history and analytics
- Fine-tuning prompts for better results

## Limitations (POC)

- No write operations
- No auto-scheduling/alerts
- No multi-tenant authentication
- Not a replacement for BI dashboards

## Contributing

This is currently a personal project. Contributions and suggestions welcome!

## License

[Add your license here]

## Database Initialization

The `scripts/init_database.py` script automatically creates the database with sample data:

- **50 users** from 10 different countries
- **12 products** across 5 categories
- **150+ orders** distributed across the last 6 months
- Realistic data distribution (85% completed, 10% pending, 5% cancelled orders)

Run it with:
```bash
python scripts/init_database.py
```

Use `--reset` to recreate the database:
```bash
python scripts/init_database.py --reset
```

The script will:
1. Create all tables matching `metadata/schema.json`
2. Insert sample data
3. Verify the data and test metrics
4. Show summary statistics

## Acknowledgments

- Built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- Uses [SQLite](https://www.sqlite.org/) for analytics (via LangChain SQLDatabase)
- SQL parsing with [sqlglot](https://github.com/tobymao/sqlglot)
- LLM integration with [Ollama](https://ollama.ai/) and [LangChain](https://www.langchain.com/)
- SQL agent tools from [LangChain SQL Toolkit](https://python.langchain.com/docs/integrations/toolkits/sql_database)
- Prompt management inspired by best practices for LLM applications


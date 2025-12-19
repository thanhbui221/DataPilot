# Project Design Document
## DataPilot - AI Data Analyst Agent (Telegram Bot, Open-Source LLM, SQL-Aware)

## 1. Goal & Scope (POC)

### Goal

Build a Telegram-based AI Data Analyst Agent that:

- Understands business questions
- Clarifies intent with the user
- Generates safe, performant SQL
- Optionally executes SQL (read-only)
- Produces human-readable insights

### Non-goals (POC)

- No write operations
- No auto-scheduling / alerts
- No multi-tenant auth
- No BI dashboard replacement

## 2. High-Level Architecture

```
Telegram User
   ↓
Telegram Bot (State Machine)
   ↓
Agent 1: Intent Clarifier (LLM)
   ↓ (confirmed intent)
Schema Selector Tool
   ↓
Agent 2: SQL Generator (LLM)
   ↓
State C: SQL Validator & Cost Guard (TOOLS)
   ↺ (feedback loop to Agent 2 if invalid)
   ↓
User Decision: Run SQL?
   ├─ No → Return SQL + Explanation
   └─ Yes
        ↓
State D: SQL Executor (READ-ONLY TOOL)
        ↓
Result Reducer Tool
        ↓
Agent 4: Insight Generator (LLM)
        ↓
Telegram Response
```

## 3. Technology Choices (POC Defaults)

### LLMs (Open Source)

**Option A: Unified Model (Recommended for POC/Phase 1)**
- Single model: Mistral-7B or LLaMA-3-8B ? (TBD)
- Role-specific prompts for each agent
- Simpler deployment and resource management

**Option B: Specialized Models (Phase 2)**

| Role              | Model                      |
| ----------------- | -------------------------- |
| Intent Clarifier  | LLaMA-3-8B / Mistral-7B    |
| SQL Generator     | CodeLLaMA-7B / StarCoder-2 |
| Insight Generator | Mistral-7B / LLaMA-3-8B    |

**Run via:**
- **Ollama** (current implementation) - Easy local deployment
- LangChain integration for unified API
- Quantized models (automatically handled by Ollama)

### Data Layer

- **SQLite** (current implementation) - Simple, reliable for POC
- LangChain SQLDatabase for connection management
- Pandas for result reduction

### SQL Safety

- sqlglot for parsing & AST checks

### Bot

- python-telegram-bot

### State Management

- SQLite (local) or Redis (optional, for production-like testing)

### Logging

- Structured logging (JSON format) using Python logging module

## 4. Core Components

### 4.1 Metadata Store (Preloaded)

**Purpose:** Provide schema & metrics to Agent 2 before SQL generation.

**Stored Data:**
- Tables & descriptions
- Columns & types
- Join relationships
- Partition keys
- Metric definitions (semantic layer)

**Format (POC):**
```
/metadata
  schema.json
  metrics.yaml
```

**Example (metrics.yaml):**
```yaml
total_revenue:
  description: Completed order revenue
  table: orders
  sql: SUM(amount)
  filters:
    status: completed
```

### 4.2 Agent 1 — Intent Clarifier

**Input:**
- User message (natural language)
- Conversation context (last N messages, optional)

**Output (Structured JSON):**
```json
{
  "metric": "total_revenue",
  "dimensions": ["country"],
  "time_range": "last_month",
  "comparison": "previous_month",
  "needs_confirmation": false,
  "confidence": 0.85
}
```

**Behavior:**
- Ask clarification questions if ambiguity affects meaning
- Loop until `needs_confirmation = false` OR `max_clarification_rounds` (default: 2) reached
- If max rounds reached, proceed with best guess and flag low confidence
- Maintain conversation context for follow-up questions (e.g., "same but for last quarter")

### 4.3 Schema Selector Tool

**Purpose:** Return only relevant schema to Agent 2.

**Input:**
```json
{
  "metric": "total_revenue",
  "dimensions": ["country"]
}
```

**Output:**
```json
{
  "tables": ["orders", "users"],
  "columns": {
    "orders": ["order_id", "user_id", "amount", "status", "created_at"],
    "users": ["user_id", "country"]
  },
  "joins": ["orders.user_id = users.user_id"],
  "partition": "orders.created_at"
}
```

### 4.4 Agent 2 — SQL Generator

**Input:**
- Confirmed intent
- Selected schema slice
- Metric SQL template

**Output:**
```json
{
  "sql": "SELECT country, SUM(amount) AS revenue FROM ..."
}
```

**Rules:**
- SELECT only
- No SELECT *
- Must respect metric definitions
- Must include time filters if partitioned

## 5. State C — SQL Validator & Cost Guard (TOOLS, NOT LLM)

### Responsibilities

- Parse SQL AST
- Enforce safety rules
- Estimate cost / row count (via EXPLAIN or sampling)
- Reject or approve

### Tooling

- `sqlglot.parse_one(sql)` for SQL parsing and AST checks
- SQLite for execution (via LangChain SQLDatabase)

### Rules

- Allow only SELECT
- Block DDL / DML
- No cross joins
- Require LIMIT if not aggregated (default: 5000)
- Require partition filter (if table is partitioned)
- Max estimated rows: 10,000 (warn if exceeded)
- Block subqueries with no LIMIT

### Output

**Rejected:**
```json
{
  "approved": false,
  "reason": "Missing time filter on partitioned column created_at",
  "estimated_rows": null,
  "estimated_cost": null
}
```

**Approved:**
```json
{
  "approved": true,
  "estimated_rows": 1500,
  "estimated_cost": "low",
  "warnings": []
}
```

### Feedback Loop

- If rejected → pass reason to Agent 2
- Max retries: 2
- If still invalid after max retries → return error to user with explanation

## 6. User Execution Decision

Telegram bot presents: *"SQL validated. Do you want to run this query?"*

**Buttons:**
- ▶️ Run query
- 🧾 Show SQL only
- ✏️ Modify SQL (new feature - allows direct SQL editing)
- 🔄 Modify intent
- ❌ Cancel

## 7. State D — SQL Executor (Tool)

### Characteristics

- Read-only connection (enforced at connection level)
- Hard timeout: 30 seconds (configurable)
- Row cap: 5,000 rows (configurable)
- Automatic LIMIT injection if missing (safety fallback)

### Error Handling

- Timeout → return user-friendly error
- Connection error → retry once, then fail gracefully
- Query error → return sanitized error message (no internal details)

### POC Implementation

```python
# Uses LangChain SQLDatabase for execution
from langchain_community.utilities import SQLDatabase
db = SQLDatabase.from_uri("sqlite:///data/sample.db")
result = db.run(sql)  # Returns string, parsed to DataFrame
```

### Query Logging

- Log all executed queries (sanitized) for audit trail
- Store: query, timestamp, user_id, execution_time, row_count

## 8. Result Reducer Tool (Critical)

**Purpose:** Prepare compact, LLM-friendly input.

**Implementation:** Pandas-based data reduction

**Operations:**
- Row count
- Aggregates (sum, avg, min, max for numeric columns)
- Top-N breakdown (by first dimension column)
- % change vs comparison (if comparison data provided)
- Sampling (≤20 rows by default)

**Output Example:**
```json
{
  "row_count": 30,
  "summary": {
    "total": 382901.2,
    "mom_change_pct": 8.3
  },
  "top_breakdown": [
    {"country": "SG", "share": 0.42},
    {"country": "VN", "share": 0.31}
  ]
}
```

## 9. Agent 4 — Insight Generator

**Implementation:** LangChain + Ollama (ChatOllama) with prompt templates

**Input:**
- Reduced result JSON
- Original question
- Metric description

**Output:**
- Executive summary
- Key drivers
- Caveats
- Suggested next questions

**Behavior:**
- Uses prompts from `prompts.yaml` for consistency
- Handles empty results gracefully with helpful suggestions
- Generates actionable insights from query results

## 10. Telegram Bot State Machine

### States

**WAITING_FOR_QUESTION**
- Initial state, ready for user input
- Can handle /start, /help commands

**CLARIFYING_INTENT**
- Agent 1 asking follow-up questions
- Max rounds: 2 (configurable)

**CONFIRM_INTENT**
- Show structured intent to user for confirmation
- User can accept or modify

**GENERATING_SQL**
- Agent 2 generating SQL
- Show "thinking" indicator

**VALIDATING_SQL**
- SQL Validator checking query
- If invalid, loop back to GENERATING_SQL (max 2 retries)

**AWAIT_RUN_DECISION**
- Present validated SQL with options
- Buttons: Run, Show SQL, Modify, Cancel

**EXECUTING**
- Running SQL query
- Show progress indicator

**GENERATING_INSIGHT**
- Agent 4 generating insights
- Show "analyzing" indicator

**DONE**
- Present final insights
- Return to WAITING_FOR_QUESTION

### Error States

**ERROR**
- Handle any errors gracefully
- Log error details
- Return user-friendly message
- Return to WAITING_FOR_QUESTION

### State Persistence

- Store state in SQLite/Redis per user_id
- Enables recovery after bot restart
- Supports conversation context

## 11. Repo Structure (POC)

```
/src
/agents
  intent_clarifier.py
  sql_generator.py
  insight_generator.py
    base_agent.py (shared LLM interface)

/tools
  schema_selector.py
  sql_validator.py
  sql_executor.py
  result_reducer.py

  /bot
    telegram_bot.py
    states.py
    handlers.py
    keyboards.py (button layouts)

  /config
    config.yaml (all configuration)
    prompts/ (YAML files for each agent's prompts)
      intent_clarifier.yaml
      sql_generator.yaml
      insight_generator.yaml

  /utils
    logger.py (structured logging setup)
    db.py (SQLite connection manager via LangChain SQLDatabase)
    state_store.py (state persistence)

/metadata
  schema.json
  metrics.yaml

/tests
  /unit
    test_agents.py
    test_tools.py
  /integration
    test_flows.py

/data
  sample.db (SQLite sample database for testing)

main.py
requirements.txt
README.md
.gitignore
```

## 12. Configuration Management

All configuration in `/src/config/config.yaml`:

```yaml
telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  
llm:
  model_name: "mistral"  # Ollama model name (e.g., "mistral", "llama3", "codellama:7b")
  base_url: "http://localhost:11434"  # Optional, defaults to localhost:11434
  temperature: 0.7
  max_tokens: 2048
  timeout: 60
  
database:
  db_uri: "sqlite:///data/sample.db"
  read_only: true
  query_timeout: 30
  max_rows: 5000
  
sql_validator:
  max_retries: 2
  require_limit: true
  max_estimated_rows: 10000
  require_partition_filter: true
  
intent_clarifier:
  max_clarification_rounds: 2
  confidence_threshold: 0.7
  
logging:
  level: "INFO"
  format: "json"
  file: "logs/datapilot.log"
  
state_store:
  type: "sqlite"  # or "redis"
  path: "./data/state.db"
```

### Environment Variables

- `TELEGRAM_BOT_TOKEN` (required)
- `MODEL_PATH` (optional, overrides config)
- `DB_URI` (optional, overrides config, e.g., "sqlite:///data/sample.db")

## 13. Error Handling & Resilience

### Agent-Level Errors

- Retry logic: 2 retries with exponential backoff
- Graceful degradation: If LLM fails, return structured error
- Timeout handling: All LLM calls have timeout (60s default)

### Tool-Level Errors

- SQL Validator: Always returns structured response (never crashes)
- SQL Executor: Catches all exceptions, returns user-friendly error
- Result Reducer: Handles empty results, malformed data gracefully

### Bot-Level Errors

- Try-catch around all state transitions
- Log all errors with context
- Return to WAITING_FOR_QUESTION on unexpected errors
- Notify user of error with actionable message

## 14. Logging & Monitoring

### Structured Logging (JSON)

Each log entry includes:
- timestamp
- level (DEBUG, INFO, WARNING, ERROR)
- component (agent/tool/bot)
- user_id (if available)
- state
- message/error details

**Example:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "component": "sql_generator",
  "user_id": 12345,
  "state": "GENERATING_SQL",
  "message": "Generated SQL query",
  "sql_preview": "SELECT country, SUM(amount)..."
}
```

### Metrics to Track (Future)

- Query success rate
- Average response time per agent
- SQL validation failure rate
- User satisfaction (via feedback buttons)

## 15. Conversation Context Management

### Context Window

- Store last 5 messages per user
- Include: user message, bot response, intent, SQL (if generated)

### Follow-up Questions

Detect references like:
- "same but for last quarter"
- "show me the breakdown"
- "what about last year?"

### Context Injection

- Include relevant context in Agent 1 and Agent 4 prompts
- Format: "Previous conversation: [summary]"

## 16. Testing Strategy

### Unit Tests

- Test each agent with mock LLM responses
- Test each tool with sample inputs
- Test SQL validator with various query types (valid/invalid)

### Integration Tests

- End-to-end flow with sample data
- Test state machine transitions
- Test error recovery

### SQL Test Suite

- Known-good queries with expected results
- Test SQL generation against expected patterns
- Validate safety rules enforcement

## 17. Implementation Phases

### Phase 1: MVP (Week 1-2)

- Basic Telegram bot with state machine
- Single unified LLM model
- Hardcoded schema.json
- Basic SQL validator (safety rules only)
- SQL executor with SQLite (via LangChain SQLDatabase)
- Simple result reducer
- Basic insight generator
- Configuration management

### Phase 2: Enhancement (Week 3-4)

- Intent clarifier with feedback loop
- Cost estimation in validator
- Query history logging
- Better error handling
- Conversation context
- Enhanced prompts

### Phase 3: Polish (Week 5+)

- Multi-model support (if needed)
- Advanced result reduction
- Query templates/saved queries
- Comprehensive testing
- Documentation

## 18. Why This POC Is Strong

- ✅ Correct agent/tool separation
- ✅ Real SQL safety model
- ✅ Human-in-the-loop execution
- ✅ Open-source LLM friendly
- ✅ Scales to production design
- ✅ Comprehensive error handling
- ✅ Structured logging for debugging
- ✅ Configuration-driven for easy iteration
- ✅ Testable architecture

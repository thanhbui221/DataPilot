Project Design Document
DataPilot - AI Data Analyst Agent (Telegram Bot, Open-Source LLM, SQL-Aware)

1. Goal & Scope (POC)
Goal

Build a Telegram-based AI Data Analyst Agent that:

Understands business questions

Clarifies intent with the user

Generates safe, performant SQL

Optionally executes SQL (read-only)

Produces human-readable insights

Non-goals (POC)

No write operations

No auto-scheduling / alerts

No multi-tenant auth

No BI dashboard replacement

2. High-Level Architecture
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

3. Technology Choices (POC Defaults)
LLMs (Open Source)
| Role              | Model                      |
| ----------------- | -------------------------- |
| Intent Clarifier  | LLaMA-3-8B / Mistral-7B    |
| SQL Generator     | CodeLLaMA-7B / StarCoder-2 |
| Insight Generator | Mistral-7B / LLaMA-3-8B    |


Run via:

llama.cpp, vLLM, or transformers

Quantized (4-bit / 8-bit)

Data Layer

DuckDB (local POC)

Pandas for result reduction

SQL Safety

sqlglot for parsing & AST checks

Bot

python-telegram-bot


4. Core Components
4.1 Metadata Store (Preloaded)
Purpose
Provide schema & metrics to Agent 2 before SQL generation.

Stored Data

Tables & descriptions

Columns & types

Join relationships

Partition keys

Metric definitions (semantic layer)

Format (POC)
/metadata
  schema.json
  metrics.yaml

Example (metrics.yaml):
total_revenue:
  description: Completed order revenue
  table: orders
  sql: SUM(amount)
  filters:
    status: completed

4.2 Agent 1 — Intent Clarifier
Input

User message (natural language)

Output (Structured JSON)
{
  "metric": "total_revenue",
  "dimensions": ["country"],
  "time_range": "last_month",
  "comparison": "previous_month",
  "needs_confirmation": false
}

Behavior
Ask clarification questions if ambiguity affects meaning

Loop until needs_confirmation = false

4.3 Schema Selector Tool
Purpose
Return only relevant schema to Agent 2.

Input
{
  "metric": "total_revenue",
  "dimensions": ["country"]
}

Output
{
  "tables": ["orders", "users"],
  "columns": {
    "orders": ["order_id", "user_id", "amount", "status", "created_at"],
    "users": ["user_id", "country"]
  },
  "joins": ["orders.user_id = users.user_id"],
  "partition": "orders.created_at"
}

4.4 Agent 2 — SQL Generator
Input

Confirmed intent

Selected schema slice

Metric SQL template

Output
{
  "sql": "SELECT country, SUM(amount) AS revenue FROM ..."
}


Rules

SELECT only

No SELECT *

Must respect metric definitions

Must include time filters if partitioned

5. State C — SQL Validator & Cost Guard (TOOLS, NOT LLM)
Responsibilities

Parse SQL AST

Enforce safety rules

Estimate cost / row count

Reject or approve

Tooling

sqlglot.parse_one(sql)

Rules

Allow only SELECT

Block DDL / DML

No cross joins

Require LIMIT if not aggregated

Require partition filter

Output
{
  "approved": false,
  "reason": "Missing time filter on partitioned column created_at"
}


Feedback Loop

If rejected → pass reason to Agent 2

Max retries: 2

6. User Execution Decision
Telegram bot presents:
“SQL validated. Do you want to run this query?”

Buttons:

▶️ Run query

🧾 Show SQL only

✏️ Modify intent

❌ Cancel


7. State D — SQL Executor (Tool)
Characteristics

Read-only connection

Timeout (e.g. 30s)

Row cap (e.g. 5,000)

POC Implementation
duckdb.connect().execute(sql).df()


8. Result Reducer Tool (Critical)
Purpose
Prepare compact, LLM-friendly input.

Operations

Row count

Aggregates

Top-N breakdown

% change vs comparison

Sampling (≤20 rows)

Output Example
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


9. Agent 4 — Insight Generator
Input

Reduced result JSON

Original question

Metric description


Output

Executive summary

Key drivers

Caveats

Suggested next questions


10. Telegram Bot State Machine
States:

WAITING_FOR_QUESTION

CLARIFYING_INTENT

CONFIRM_INTENT

GENERATING_SQL

VALIDATING_SQL

AWAIT_RUN_DECISION

EXECUTING

GENERATING_INSIGHT

DONE

11. Repo Structure (POC)
/agents
  intent_clarifier.py
  sql_generator.py
  insight_generator.py

/tools
  schema_selector.py
  sql_validator.py
  sql_executor.py
  result_reducer.py

/metadata
  schema.json
  metrics.yaml

/bot
  telegram_bot.py
  states.py

/main.py


12. Why This POC Is Strong

Correct agent/tool separation

Real SQL safety model

Human-in-the-loop execution

Open-source LLM friendly

Scales to production design




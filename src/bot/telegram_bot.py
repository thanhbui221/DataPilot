"""Main Telegram bot implementation."""
import os
import yaml
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import logging

from ..utils.logger import setup_logger
from ..utils.db import DatabaseManager
from ..utils.state_store import StateStore
from ..agents.intent_clarifier import IntentClarifier
from ..agents.sql_generator import SQLGenerator
from ..agents.insight_generator import InsightGenerator
from ..tools.schema_selector import SchemaSelector
from ..tools.sql_validator import SQLValidator
from ..tools.sql_executor import SQLExecutor
from ..tools.result_reducer import ResultReducer
from .handlers import (
    handle_start, handle_help, handle_message, handle_callback_query
)

logger = logging.getLogger("datapilot")


class DataPilotBot:
    """Main DataPilot Telegram bot."""
    
    def __init__(self, config_path: str = "./src/config/config.yaml"):
        """
        Initialize DataPilot bot.
        
        Args:
            config_path: Path to configuration YAML file
        """
        self.config = self._load_config(config_path)
        
        # Setup logging
        setup_logger(self.config.get("logging", {}))
        logger.info("DataPilot bot initializing...")
        
        # Initialize components
        self.db_manager = DatabaseManager(
            self.config["database"]["db_uri"],
            read_only=self.config["database"]["read_only"]
        )
        
        self.state_store = StateStore(
            self.config["state_store"]["type"],
            self.config["state_store"]["path"]
        )
        
        # Initialize agents
        llm_config = self.config["llm"]
        
        # Build common LLM args - only include base_url if specified in config
        llm_kwargs = {
            "model_name": llm_config["model_name"],
            "temperature": llm_config["temperature"],
            "max_tokens": llm_config["max_tokens"],
            "timeout": llm_config["timeout"]
        }
        if llm_config.get("base_url"):
            llm_kwargs["base_url"] = llm_config["base_url"]
        
        self.intent_clarifier = IntentClarifier(
            **llm_kwargs,
            max_clarification_rounds=self.config["intent_clarifier"]["max_clarification_rounds"],
            confidence_threshold=self.config["intent_clarifier"]["confidence_threshold"]
        )
        
        self.sql_generator = SQLGenerator(**llm_kwargs)
        
        self.insight_generator = InsightGenerator(**llm_kwargs)
        
        # Initialize tools
        self.schema_selector = SchemaSelector(
            schema_path="./metadata/schema.json",
            metrics_path="./metadata/metrics.yaml"
        )
        
        self.sql_validator = SQLValidator(
            max_estimated_rows=self.config["sql_validator"]["max_estimated_rows"],
            require_limit=self.config["sql_validator"]["require_limit"],
            require_partition_filter=self.config["sql_validator"]["require_partition_filter"]
        )
        
        # SQL executor needs LLM for LangChain toolkit - use intent_clarifier's LLM
        # Note: LLM is initialized in IntentClarifier.__init__, so it should be available
        self.sql_executor = SQLExecutor(
            self.db_manager,
            llm=self.intent_clarifier._llm,
            timeout=self.config["database"]["query_timeout"],
            max_rows=self.config["database"]["max_rows"]
        )
        
        self.result_reducer = ResultReducer()
        
        # Initialize Telegram bot
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN") or self.config["telegram"]["bot_token"]
        if bot_token.startswith("${") and bot_token.endswith("}"):
            # Environment variable placeholder
            var_name = bot_token[2:-1]
            bot_token = os.getenv(var_name)
        
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in environment or config")
        
        self.application = Application.builder().token(bot_token).build()
        self._setup_handlers()
        
        logger.info("DataPilot bot initialized successfully")
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def _setup_handlers(self):
        """Setup Telegram bot handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", handle_start))
        self.application.add_handler(CommandHandler("help", handle_help))
        
        # Message handler
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                lambda u, c: handle_message(
                    u, c, self.state_store, self.intent_clarifier,
                    self.schema_selector, self.sql_generator, self.sql_validator,
                    self.sql_executor, self.result_reducer, self.insight_generator
                )
            )
        )
        
        # Callback query handler
        self.application.add_handler(
            CallbackQueryHandler(
                lambda u, c: handle_callback_query(
                    u, c, self.state_store, self.schema_selector,
                    self.sql_generator, self.sql_validator, self.sql_executor,
                    self.result_reducer, self.insight_generator
                )
            )
        )
    
    def run(self):
        """Start the bot."""
        logger.info("Starting DataPilot bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    def stop(self):
        """Stop the bot."""
        logger.info("Stopping DataPilot bot...")
        self.db_manager.close()
        self.application.stop()


"""Telegram bot message and callback handlers."""
from typing import Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from .states import BotState
import logging

logger = logging.getLogger("datapilot")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome_message = """
👋 Welcome to DataPilot!

I'm your AI Data Analyst assistant. I can help you:
• Ask questions about your data in natural language
• Generate SQL queries safely
• Execute queries and provide insights

Just ask me a question like:
"What's our total revenue by country?"

Type /help for more information.
    """.strip()
    
    await update.message.reply_text(welcome_message)


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_message = """
📖 DataPilot Help

**Commands:**
/start - Start the bot
/help - Show this help message

**How to use:**
1. Ask a question about your data
2. I'll clarify if needed
3. Review the generated SQL
4. Choose to run it or modify

**Example questions:**
• "What's our total revenue?"
• "Show me sales by country"
• "Compare this month to last month"

**Safety:**
• All queries are read-only
• SQL is validated before execution
• Large queries are automatically limited
    """.strip()
    
    await update.message.reply_text(help_message, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        bot_state_manager, intent_clarifier, schema_selector,
                        sql_generator, sql_validator, sql_executor,
                        result_reducer, insight_generator):
    """
    Handle incoming text messages.
    
    This is the main message handler that routes to appropriate state handlers.
    """
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Get current state
    state = bot_state_manager.get_state(user_id)
    if not state:
        state = BotState.WAITING_FOR_QUESTION.value
        bot_state_manager.set_state(user_id, state)
    
    logger.info(f"User {user_id} in state {state}: {message_text}")
    
    # Route to state handler
    if state == BotState.WAITING_FOR_QUESTION.value:
        await handle_waiting_for_question(
            update, context, bot_state_manager, intent_clarifier
        )
    elif state == BotState.CLARIFYING_INTENT.value:
        await handle_clarifying_intent(
            update, context, bot_state_manager, intent_clarifier
        )
    # TODO: Add handlers for other states
    else:
        await update.message.reply_text(
            f"State {state} handler not yet implemented. Please use /start to reset."
        )


async def handle_waiting_for_question(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                      bot_state_manager, intent_clarifier):
    """Handle messages in WAITING_FOR_QUESTION state."""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Show thinking indicator
    thinking_msg = await update.message.reply_text("🤔 Analyzing your question...")
    
    try:
        # Get conversation context
        conversation_context = bot_state_manager.get_recent_messages(user_id, limit=5)
        
        # Clarify intent
        intent = intent_clarifier.clarify_intent(message_text, conversation_context)
        
        # Store intent in context
        bot_state_manager.set_state(user_id, BotState.CLARIFYING_INTENT.value, {
            "intent": intent,
            "original_question": message_text
        })
        
        # Delete thinking message
        await thinking_msg.delete()
        
        if intent.get("needs_confirmation"):
            # Ask clarification question
            clarification = intent_clarifier.ask_clarification(intent)
            await update.message.reply_text(clarification)
        else:
            # Move to confirm intent
            await handle_intent_confirmed(update, context, bot_state_manager, intent)
            
    except Exception as e:
        logger.error(f"Error in handle_waiting_for_question: {str(e)}")
        await thinking_msg.delete()
        await update.message.reply_text(
            "❌ Sorry, I encountered an error processing your question. Please try again."
        )
        bot_state_manager.set_state(user_id, BotState.ERROR.value)


async def handle_clarifying_intent(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                    bot_state_manager, intent_clarifier):
    """Handle clarification responses."""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Get stored intent
    state_data = bot_state_manager.get_state(user_id)
    if not state_data or "intent" not in state_data.get("context", {}):
        await update.message.reply_text("Please start over with /start")
        return
    
    # TODO: Update intent based on clarification
    # For now, move forward
    intent = state_data["context"]["intent"]
    await handle_intent_confirmed(update, context, bot_state_manager, intent)


async def handle_intent_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                  bot_state_manager, intent):
    """Handle confirmed intent - move to SQL generation."""
    user_id = update.effective_user.id
    
    # Show intent summary
    intent_summary = f"""
✅ Intent confirmed:
• Metric: {intent.get('metric', 'N/A')}
• Dimensions: {', '.join(intent.get('dimensions', [])) or 'None'}
• Time range: {intent.get('time_range', 'N/A')}
    """.strip()
    
    from .keyboards import get_confirm_intent_keyboard
    await update.message.reply_text(
        intent_summary,
        reply_markup=get_confirm_intent_keyboard()
    )
    
    bot_state_manager.set_state(user_id, BotState.CONFIRM_INTENT.value, {
        "intent": intent
    })


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                bot_state_manager, schema_selector, sql_generator,
                                sql_validator, sql_executor, result_reducer,
                                insight_generator):
    """Handle inline keyboard callback queries."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    callback_data = query.data
    
    logger.info(f"Callback from user {user_id}: {callback_data}")
    
    if callback_data == "confirm_intent":
        # Move to SQL generation
        await handle_generate_sql(
            query, context, bot_state_manager, schema_selector,
            sql_generator, sql_validator
        )
    elif callback_data == "run_query":
        # Execute SQL
        await handle_execute_sql(
            query, context, bot_state_manager, sql_executor,
            result_reducer, insight_generator
        )
    elif callback_data == "show_sql":
        # Show SQL only
        state_data = bot_state_manager.get_state(user_id)
        sql = state_data.get("context", {}).get("sql", "No SQL available")
        await query.edit_message_text(f"```sql\n{sql}\n```", parse_mode="Markdown")
    elif callback_data == "modify_intent":
        # Return to question input
        bot_state_manager.set_state(user_id, BotState.WAITING_FOR_QUESTION.value)
        await query.edit_message_text("Please ask your question again.")
    elif callback_data == "cancel":
        # Cancel and reset
        bot_state_manager.set_state(user_id, BotState.WAITING_FOR_QUESTION.value)
        await query.edit_message_text("Cancelled. Ask me a new question!")


async def handle_generate_sql(query, context, bot_state_manager, schema_selector,
                              sql_generator, sql_validator):
    """Handle SQL generation flow."""
    user_id = query.from_user.id
    
    await query.edit_message_text("🔧 Generating SQL query...")
    
    try:
        # Get intent
        state_data = bot_state_manager.get_state(user_id)
        intent = state_data["context"]["intent"]
        
        # Select schema
        schema_slice = schema_selector.select_schema(intent)
        metric_def = schema_slice.pop("metric")
        
        # Generate SQL
        bot_state_manager.set_state(user_id, BotState.GENERATING_SQL.value)
        sql_result = sql_generator.generate_sql(intent, schema_slice, metric_def)
        sql = sql_result["sql"]
        
        # Validate SQL
        bot_state_manager.set_state(user_id, BotState.VALIDATING_SQL.value)
        validation = sql_validator.validate(sql, schema_slice.get("partition"))
        
        if not validation["approved"]:
            # Retry generation with feedback
            # TODO: Implement retry logic
            await query.edit_message_text(
                f"❌ SQL validation failed: {validation['reason']}\n\nPlease try rephrasing your question."
            )
            bot_state_manager.set_state(user_id, BotState.ERROR.value)
            return
        
        # Store SQL and move to decision
        bot_state_manager.set_state(user_id, BotState.AWAIT_RUN_DECISION.value, {
            "intent": intent,
            "sql": sql,
            "validation": validation
        })
        
        from .keyboards import get_run_decision_keyboard
        await query.edit_message_text(
            f"✅ SQL validated successfully!\n\n```sql\n{sql}\n```\n\nDo you want to run this query?",
            reply_markup=get_run_decision_keyboard(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in handle_generate_sql: {str(e)}")
        await query.edit_message_text(
            "❌ Error generating SQL. Please try again."
        )
        bot_state_manager.set_state(user_id, BotState.ERROR.value)


async def handle_execute_sql(query, context, bot_state_manager, sql_executor,
                             result_reducer, insight_generator):
    """Handle SQL execution flow."""
    user_id = query.from_user.id
    
    await query.edit_message_text("⚙️ Executing query...")
    
    try:
        # Get SQL
        state_data = bot_state_manager.get_state(user_id)
        sql = state_data["context"]["sql"]
        intent = state_data["context"]["intent"]
        
        # Execute
        bot_state_manager.set_state(user_id, BotState.EXECUTING.value)
        result = sql_executor.execute(sql, user_id=user_id)
        
        if not result["success"]:
            await query.edit_message_text(
                f"❌ Query execution failed: {result['error']}"
            )
            bot_state_manager.set_state(user_id, BotState.ERROR.value)
            return
        
        # Reduce results
        reduced = result_reducer.reduce(result["data"])
        
        # Generate insights
        bot_state_manager.set_state(user_id, BotState.GENERATING_INSIGHT.value)
        insights = insight_generator.generate_insights(
            reduced,
            state_data["context"].get("original_question", ""),
            "Metric description"  # TODO: Get from metrics.yaml
        )
        
        # Present results
        bot_state_manager.set_state(user_id, BotState.DONE.value)
        await query.edit_message_text(insights)
        
        # Reset to waiting
        bot_state_manager.set_state(user_id, BotState.WAITING_FOR_QUESTION.value)
        
    except Exception as e:
        logger.error(f"Error in handle_execute_sql: {str(e)}")
        await query.edit_message_text(
            "❌ Error executing query. Please try again."
        )
        bot_state_manager.set_state(user_id, BotState.ERROR.value)


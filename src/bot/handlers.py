"""Telegram bot message and callback handlers."""
from typing import Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from .states import BotState
import logging
import html

logger = logging.getLogger("datapilot")


def escape_sql_for_telegram(sql: str) -> str:
    """
    Escape SQL for safe display in Telegram messages.
    
    For Markdown mode, we need to escape special characters.
    For HTML mode, we use html.escape().
    """
    # Escape HTML entities (safer for both Markdown and HTML)
    return html.escape(sql)


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
    state_data = bot_state_manager.get_state(user_id)
    if not state_data:
        current_state = BotState.WAITING_FOR_QUESTION.value
        bot_state_manager.set_state(user_id, current_state)
    else:
        current_state = state_data.get("state", BotState.WAITING_FOR_QUESTION.value)
    
    logger.info(f"User {user_id} in state {current_state}: {message_text}")
    
    # Route to state handler
    if current_state == BotState.WAITING_FOR_QUESTION.value:
        await handle_waiting_for_question(
            update, context, bot_state_manager, intent_clarifier
        )
    elif current_state == BotState.CLARIFYING_INTENT.value:
        await handle_clarifying_intent(
            update, context, bot_state_manager, intent_clarifier
        )
    elif current_state == BotState.CONFIRM_INTENT.value:
        # User can type to modify, treat as new question
        await handle_waiting_for_question(
            update, context, bot_state_manager, intent_clarifier
        )
    elif current_state == BotState.ERROR.value:
        # Reset to waiting state on error and try to process message
        await handle_error_state(update, context, bot_state_manager, intent_clarifier)
    elif current_state == BotState.AWAIT_RUN_DECISION.value:
        # User sent text instead of clicking button - treat as new question
        await handle_await_run_decision_text(update, context, bot_state_manager, intent_clarifier)
    elif current_state == BotState.EDITING_SQL.value:
        # User is editing SQL
        await handle_editing_sql(update, context, bot_state_manager, sql_validator)
    # TODO: Add handlers for other states
    else:
        await update.message.reply_text(
            f"State {current_state} handler not yet implemented. Please use /start to reset."
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
        logger.error(f"Error in handle_waiting_for_question: {str(e)}", exc_info=True)
        try:
            await thinking_msg.delete()
        except:
            pass
        await update.message.reply_text(
            f"❌ Sorry, I encountered an error processing your question: {str(e)}\n\n"
            "Please try asking again or use /start to reset."
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
        bot_state_manager.set_state(user_id, BotState.WAITING_FOR_QUESTION.value)
        return
    
    # Get the stored intent
    stored_intent = state_data["context"]["intent"]
    original_question = state_data["context"].get("original_question", message_text)
    
    # Re-clarify intent with the new user response
    # Combine original question with clarification response
    combined_question = f"{original_question} {message_text}"
    conversation_context = bot_state_manager.get_recent_messages(user_id, limit=5)
    
    try:
        # Re-clarify with combined context
        updated_intent = intent_clarifier.clarify_intent(combined_question, conversation_context)
        
        # Update stored intent
        bot_state_manager.set_state(user_id, BotState.CLARIFYING_INTENT.value, {
            "intent": updated_intent,
            "original_question": original_question
        })
        
        if updated_intent.get("needs_confirmation") and updated_intent.get("confidence", 0) < intent_clarifier.confidence_threshold:
            # Still needs clarification
            clarification = intent_clarifier.ask_clarification(updated_intent)
            await update.message.reply_text(clarification)
        else:
            # Good enough, move to confirmation
            await handle_intent_confirmed(update, context, bot_state_manager, updated_intent)
            
    except Exception as e:
        logger.error(f"Error in handle_clarifying_intent: {str(e)}")
        # Fallback: use stored intent
        await handle_intent_confirmed(update, context, bot_state_manager, stored_intent)


async def handle_error_state(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             bot_state_manager, intent_clarifier):
    """Handle ERROR state - reset to waiting for question and try to process message."""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Reset to waiting state first
    bot_state_manager.set_state(user_id, BotState.WAITING_FOR_QUESTION.value)
    
    # Try to process the message as a new question
    await update.message.reply_text(
        "🔄 Resetting... Processing your question now."
    )
    
    # Process as new question
    await handle_waiting_for_question(
        update, context, bot_state_manager, intent_clarifier
    )


async def handle_await_run_decision_text(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                          bot_state_manager, intent_clarifier):
    """Handle text message in AWAIT_RUN_DECISION state - treat as new question."""
    user_id = update.effective_user.id
    
    # Inform user we're starting a new question
    await update.message.reply_text(
        "🔄 Starting a new question. Processing your request..."
    )
    
    # Reset to waiting state and process as new question
    bot_state_manager.set_state(user_id, BotState.WAITING_FOR_QUESTION.value)
    
    # Process as new question
    await handle_waiting_for_question(
        update, context, bot_state_manager, intent_clarifier
    )


async def handle_editing_sql(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             bot_state_manager, sql_validator):
    """Handle SQL editing - user sends modified SQL."""
    user_id = update.effective_user.id
    modified_sql = update.message.text.strip()
    
    # Remove markdown code blocks if present
    if modified_sql.startswith("```sql"):
        modified_sql = modified_sql[6:]
    if modified_sql.startswith("```"):
        modified_sql = modified_sql[3:]
    if modified_sql.endswith("```"):
        modified_sql = modified_sql[:-3]
    modified_sql = modified_sql.strip()
    
    # Get original context - handle missing keys gracefully
    state_data = bot_state_manager.get_state(user_id)
    if not state_data:
        await update.message.reply_text(
            "❌ Error: No previous context found. Please start over with /start"
        )
        bot_state_manager.set_state(user_id, BotState.WAITING_FOR_QUESTION.value)
        return
    
    context = state_data.get("context", {})
    intent = context.get("intent")
    schema_slice = context.get("schema_slice", {})
    
    if not intent:
        await update.message.reply_text(
            "❌ Error: No intent found in context. Please start over with /start"
        )
        bot_state_manager.set_state(user_id, BotState.WAITING_FOR_QUESTION.value)
        return
    
    # Validate modified SQL
    validation = sql_validator.validate(
        modified_sql, 
        schema_slice.get("partition") if schema_slice else None
    )
    
    # Store modified SQL
    bot_state_manager.set_state(user_id, BotState.AWAIT_RUN_DECISION.value, {
        "intent": intent,
        "sql": modified_sql,
        "validation": validation,
        "schema_slice": schema_slice
    })
    
    # Show validation result and options
    from .keyboards import get_run_decision_keyboard
    
    # Escape SQL for safe display
    modified_sql_escaped = escape_sql_for_telegram(modified_sql)
    
    if validation["approved"]:
        message = (
            f"✅ <b>SQL Updated and Validated</b>\n\n"
            f"Modified SQL:\n<pre><code class=\"language-sql\">{modified_sql_escaped}</code></pre>\n\n"
            f"Ready to execute!"
        )
    else:
        message = (
            f"⚠️ <b>SQL Updated with Validation Warning</b>\n\n"
            f"Warning: {html.escape(validation['reason'])}\n\n"
            f"Modified SQL:\n<pre><code class=\"language-sql\">{modified_sql_escaped}</code></pre>\n\n"
            f"Do you still want to run this query?"
        )
    
    await update.message.reply_text(
        message,
        reply_markup=get_run_decision_keyboard(),
        parse_mode="HTML"
    )


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
        # Escape SQL for safe display
        sql_escaped = escape_sql_for_telegram(sql)
        await query.edit_message_text(
            f"<pre><code class=\"language-sql\">{sql_escaped}</code></pre>",
            parse_mode="HTML"
        )
    elif callback_data == "modify_sql":
        # Enter SQL editing mode
        state_data = bot_state_manager.get_state(user_id)
        context = state_data.get("context", {})
        sql = context.get("sql", "")
        
        # Escape SQL for safe display
        sql_escaped = escape_sql_for_telegram(sql)
        
        # Preserve existing context when entering EDITING_SQL state
        bot_state_manager.set_state(user_id, BotState.EDITING_SQL.value, context)
        await query.edit_message_text(
            f"✏️ <b>Edit SQL Query</b>\n\n"
            f"Current SQL:\n<pre><code class=\"language-sql\">{sql_escaped}</code></pre>\n\n"
            f"Please send your modified SQL query. I'll validate it before execution.",
            parse_mode="HTML"
        )
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
        # Keep a copy of schema_slice for later use (validation, editing)
        schema_slice_copy = schema_slice.copy()
        
        # Generate SQL
        bot_state_manager.set_state(user_id, BotState.GENERATING_SQL.value)
        sql_result = sql_generator.generate_sql(intent, schema_slice, metric_def)
        sql = sql_result["sql"]
        
        # Validate SQL
        bot_state_manager.set_state(user_id, BotState.VALIDATING_SQL.value)
        validation = sql_validator.validate(sql, schema_slice_copy.get("partition"))
        
        if not validation["approved"]:
            # Show SQL even if validation failed, but warn user
            from .keyboards import get_run_decision_keyboard
            # Escape SQL for safe display
            sql_escaped = escape_sql_for_telegram(sql)
            await query.edit_message_text(
                f"⚠️ SQL validation warning: {validation['reason']}\n\n"
                f"Generated SQL:\n<pre><code class=\"language-sql\">{sql_escaped}</code></pre>\n\n"
                f"Do you still want to run this query?",
                reply_markup=get_run_decision_keyboard(),
                parse_mode="HTML"
            )
            # Store SQL anyway so user can see it
            bot_state_manager.set_state(user_id, BotState.AWAIT_RUN_DECISION.value, {
                "intent": intent,
                "sql": sql,
                "validation": validation,
                "schema_slice": schema_slice_copy
            })
            return
        
        # Store SQL and move to decision
        bot_state_manager.set_state(user_id, BotState.AWAIT_RUN_DECISION.value, {
            "intent": intent,
            "sql": sql,
            "validation": validation,
            "schema_slice": schema_slice_copy
        })
        
        from .keyboards import get_run_decision_keyboard
        # Escape SQL for safe display
        sql_escaped = escape_sql_for_telegram(sql)
        await query.edit_message_text(
            f"✅ SQL validated successfully!\n\n<pre><code class=\"language-sql\">{sql_escaped}</code></pre>\n\nDo you want to run this query?",
            reply_markup=get_run_decision_keyboard(),
            parse_mode="HTML"
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
        
        # Check for empty results
        df = result["data"]
        is_empty = (
            df is None or 
            df.empty or 
            len(df) == 0 or
            (len(df) == 1 and "result" in df.columns and isinstance(df.iloc[0]["result"], str) and "Could not parse" in str(df.iloc[0]["result"]))
        )
        
        if is_empty:
            # Provide helpful message for empty results
            original_question = state_data["context"].get("original_question", "")
            sql = state_data["context"]["sql"]
            
            # Escape SQL for safe display
            sql_escaped = escape_sql_for_telegram(sql)
            empty_message = (
                f"📊 <b>No Results Found</b>\n\n"
                f"Your query returned 0 rows.\n\n"
                f"<b>Query:</b>\n<pre><code class=\"language-sql\">{sql_escaped}</code></pre>\n\n"
                f"<b>Possible reasons:</b>\n"
                f"• The date range might not match available data\n"
                f"• The filters might be too restrictive\n"
                f"• The data might not exist for the specified criteria\n\n"
                f"<b>Suggestions:</b>\n"
                f"• Try a different date range\n"
                f"• Check if the filters are correct\n"
                f"• Ask about available data ranges"
            )
            
            bot_state_manager.set_state(user_id, BotState.DONE.value)
            await query.edit_message_text(empty_message, parse_mode="HTML")
            bot_state_manager.set_state(user_id, BotState.WAITING_FOR_QUESTION.value)
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


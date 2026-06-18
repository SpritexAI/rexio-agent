import os
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from rexio_agent.core.loop import AgentSession

logger = logging.getLogger("rexio_agent.gateway.telegram")

# Cache to keep track of active sessions for each chat ID
sessions = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a friendly welcome message when /start command is issued."""
    chat_id = update.effective_chat.id
    target_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if target_chat_id and str(chat_id) != str(target_chat_id):
        # Ignore unauthorized users
        return

    await update.message.reply_text("☤ Welcome to RexiO Agent Telegram Gateway! Send me any message to start the agent loop.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text messages from Telegram and runs the agent loop."""
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    target_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    # Security: If a chat ID is configured, ignore messages from any other chat
    if target_chat_id and str(chat_id) != str(target_chat_id):
        logger.warning(f"Unauthorized access attempt from chat ID {chat_id}")
        return

    user_text = update.message.text
    conv_id = f"telegram_{chat_id}"
    
    # Initialize session if not cached
    if conv_id not in sessions:
        sessions[conv_id] = AgentSession(
            platform="telegram",
            channel_id=str(chat_id),
            conversation_id=conv_id
        )
        
    session = sessions[conv_id]
    
    # Show typing status to let the user know the agent is thinking
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    try:
        # Run the agent ReAct loop in a separate thread to prevent blocking the asyncio loop
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, session.run, user_text)
        
        # Send the final response back to the user
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error executing agent session for chat {chat_id}: {str(e)}")
        await update.message.reply_text(f"⚠ An error occurred: {str(e)}")

async def run_telegram_bot() -> None:
    """Starts the Telegram bot application."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.info("TELEGRAM_BOT_TOKEN not configured. Skipping Telegram Gateway.")
        return

    logger.info("Initializing Telegram Gateway...")
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Initialize and start the application polling loop
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    logger.info("Telegram Gateway is online and polling for updates.")

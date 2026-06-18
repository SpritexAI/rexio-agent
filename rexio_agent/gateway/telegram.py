import os
import json
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from rexio_agent.core.loop import AgentSession

logger = logging.getLogger("rexio_agent.gateway.telegram")

sessions = {}

TOOL_LABELS = {
    "search_web": "🔍 Searching web",
    "read_file": "📄 Reading file",
    "write_file": "✏️ Writing file",
    "list_directory": "📁 Listing directory",
    "execute_python_code": "⚙️ Executing code",
}

def tool_label(tool: str, args: str) -> str:
    label = TOOL_LABELS.get(tool, f"🔧 {tool.replace('_', ' ').capitalize()}")
    if tool == "search_web":
        import re
        m = re.search(r"query=['\"](.+?)['\"]", args)
        q = m.group(1) if m else ""
        if q:
            label = f'🔍 Searching "{q}"'
    return label


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = os.getenv("TELEGRAM_CHAT_ID")
    if target and str(chat_id) != str(target):
        return
    await update.message.reply_text(
        "☤ Welcome to RexiO Agent! Send me any message to start."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    target = os.getenv("TELEGRAM_CHAT_ID")
    if target and str(chat_id) != str(target):
        logger.warning(f"Unauthorized access from chat {chat_id}")
        return

    user_text = update.message.text
    conv_id = f"telegram_{chat_id}"

    if conv_id not in sessions:
        sessions[conv_id] = AgentSession(
            platform="telegram",
            channel_id=str(chat_id),
            conversation_id=conv_id,
        )

    session = sessions[conv_id]

    # Send initial placeholder
    status_msg = await update.message.reply_text("☤ _Thinking..._", parse_mode="Markdown")

    # asyncio.Queue — bridge between sync generator thread and async handler
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def producer():
        """Runs run_stream() in a thread, pushes each event dict into the queue."""
        try:
            for raw in session.run_stream(user_text):
                raw = raw.strip()
                if not raw.startswith("data:"):
                    continue
                try:
                    event = json.loads(raw[5:].strip())
                    loop.call_soon_threadsafe(queue.put_nowait, event)
                except Exception:
                    pass
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": str(e)})
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "__done__"})

    # State
    completed_steps: list[str] = []
    answer_chunks: list[str] = []
    last_edit = ""

    async def safe_edit(text: str):
        nonlocal last_edit
        if text == last_edit:
            return
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=text,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
            last_edit = text
        except Exception:
            pass

    def build_status(current_action: str = "", answer: str = "") -> str:
        parts = list(completed_steps)
        if current_action:
            parts.append(current_action)
        if answer:
            parts.append(f"\n{answer}")
        return "\n".join(parts) or "☤ _Thinking..._"

    # Typing indicator
    async def keep_typing():
        try:
            while True:
                await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                await asyncio.sleep(4)
        except asyncio.CancelledError:
            pass

    typing_task = asyncio.ensure_future(keep_typing())

    # Start producer in background thread
    producer_task = loop.run_in_executor(None, producer)

    current_action = ""

    try:
        while True:
            event = await queue.get()

            if event["type"] == "__done__":
                break

            elif event["type"] == "thinking":
                current_action = f"_{tool_label(event.get('tool',''), event.get('args',''))}..._"
                await safe_edit(build_status(current_action=current_action))

            elif event["type"] == "step":
                label = tool_label(event.get("tool", ""), event.get("args", ""))
                completed_steps.append(f"✅ {label}")
                current_action = ""
                await safe_edit(build_status())

            elif event["type"] == "token":
                answer_chunks.append(event["text"])
                # Debounce: edit every ~8 tokens to avoid Telegram rate limit
                if len(answer_chunks) % 8 == 0:
                    await safe_edit(build_status(answer="".join(answer_chunks)))

            elif event["type"] == "error":
                await safe_edit(f"⚠️ {event.get('message', 'Unknown error')}")
                return

        # Final message — just the answer
        final = "".join(answer_chunks).strip()
        if final:
            await safe_edit(final)

    finally:
        typing_task.cancel()
        await producer_task


async def run_telegram_bot() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.info("TELEGRAM_BOT_TOKEN not configured. Skipping Telegram Gateway.")
        return

    logger.info("Initializing Telegram Gateway...")
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    logger.info("Telegram Gateway is online and polling for updates.")

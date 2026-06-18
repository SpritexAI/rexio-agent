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
        try:
            a = json.loads(args.replace("'", '"')) if args.startswith("{") else {}
            q = a.get("query", "")
        except Exception:
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

    # Send initial placeholder message
    status_msg = await update.message.reply_text("☤ _Thinking..._", parse_mode="Markdown")

    completed_steps: list[str] = []
    answer_chunks: list[str] = []

    def build_text(current_action: str = "", streaming_answer: str = "") -> str:
        parts = []
        for s in completed_steps:
            parts.append(s)
        if current_action:
            parts.append(current_action)
        if streaming_answer:
            parts.append(f"\n{streaming_answer}")
        return "\n".join(parts) if parts else "☤ _Thinking..._"

    last_text = ""

    async def safe_edit(text: str):
        nonlocal last_text
        if text == last_text:
            return
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=text,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
            last_text = text
        except Exception:
            pass  # Telegram ignores edits with identical content

    current_action = ""

    try:
        loop = asyncio.get_running_loop()

        def run_gen():
            return list(session.run_stream(user_text))

        # Run generator in thread, collect all events
        events_raw = await loop.run_in_executor(None, run_gen)

        # Replay events and update Telegram message progressively
        for raw in events_raw:
            # raw is already a string like "data: {...}\n\n"
            raw = raw.strip()
            if not raw.startswith("data:"):
                continue
            try:
                event = json.loads(raw[5:].strip())
            except Exception:
                continue

            if event["type"] == "thinking":
                current_action = f"_{tool_label(event.get('tool',''), event.get('args',''))}..._"
                await safe_edit(build_text(current_action=current_action))

            elif event["type"] == "step":
                label = tool_label(event.get("tool", ""), event.get("args", ""))
                completed_steps.append(f"✅ {label}")
                current_action = ""
                await safe_edit(build_text())

            elif event["type"] == "token":
                answer_chunks.append(event["text"])
                await safe_edit(build_text(streaming_answer="".join(answer_chunks)))

            elif event["type"] == "done":
                break

            elif event["type"] == "error":
                await safe_edit(f"⚠️ Error: {event.get('message','Unknown error')}")
                return

        # Final clean message — just the answer
        final = "".join(answer_chunks).strip()
        if final:
            await safe_edit(final)

    except Exception as e:
        logger.error(f"Error in agent session for chat {chat_id}: {e}")
        await safe_edit(f"⚠️ An error occurred: {str(e)}")


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

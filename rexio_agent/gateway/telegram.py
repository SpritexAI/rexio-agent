import os
import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from rexio_agent.core.loop import AgentSession
from rexio_agent.db.connection import get_pending_skills, approve_skill, reject_skill

BOT_COMMANDS = [
    ("start",  "Start RexiO Agent"),
    ("skills", "Review pending compiled skills"),
    ("memory", "Show current memory contents"),
    ("clear",  "Start a fresh conversation"),
    ("status", "Check agent status"),
]

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
    import re, ast

    # Try to parse args as a dict for richer labels
    try:
        parsed = ast.literal_eval(args) if args else {}
    except Exception:
        parsed = {}

    if tool == "search_web":
        q = parsed.get("query", "")
        if not q:
            m = re.search(r"query=['\"](.+?)['\"]", args)
            q = m.group(1) if m else ""
        return f'🔍 Searching "{q}"' if q else "🔍 Searching web"

    if tool == "execute_python_code":
        code = parsed.get("code", "")
        first_line = code.strip().splitlines()[0][:60] if code.strip() else ""
        return f"⚙️ `{first_line}`" if first_line else "⚙️ Executing code"

    if tool == "read_file":
        path = parsed.get("path", "")
        name = path.split("/")[-1] if path else ""
        return f"📄 Reading `{name}`" if name else "📄 Reading file"

    if tool == "write_file":
        path = parsed.get("path", "")
        name = path.split("/")[-1] if path else ""
        return f"✏️ Writing `{name}`" if name else "✏️ Writing file"

    if tool == "list_directory":
        path = parsed.get("path", "")
        return f"📁 Listing `{path}`" if path else "📁 Listing directory"

    return TOOL_LABELS.get(tool, f"🔧 {tool.replace('_', ' ').capitalize()}")


async def skills_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows pending skills awaiting approval."""
    chat_id = update.effective_chat.id
    target = os.getenv("TELEGRAM_CHAT_ID")
    if target and str(chat_id) != str(target):
        return

    pending = get_pending_skills()
    if not pending:
        await update.message.reply_text("✅ No pending skills. All clear.")
        return

    for skill in pending:
        preview = skill['code'][:300] + ("..." if len(skill['code']) > 300 else "")
        text = (
            f"🔧 *{skill['name']}*\n"
            f"_{skill['description']}_\n\n"
            f"```python\n{preview}\n```"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"skill_approve:{skill['name']}"),
            InlineKeyboardButton("❌ Reject",  callback_data=f"skill_reject:{skill['name']}"),
        ]])
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def skill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles approve/reject inline button presses."""
    query = update.callback_query
    await query.answer()

    action, skill_name = query.data.split(":", 1)

    if action == "skill_approve":
        approve_skill(skill_name)
        # Reload registry in all active sessions
        for session in sessions.values():
            session.registry.load_custom_skills()
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"✅ *{skill_name}* approved and activated!", parse_mode="Markdown")

    elif action == "skill_reject":
        reject_skill(skill_name)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"🗑 *{skill_name}* rejected and deleted.", parse_mode="Markdown")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = os.getenv("TELEGRAM_CHAT_ID")
    if target and str(chat_id) != str(target):
        return
    await update.message.reply_text(
        "☤ Welcome to RexiO Agent!\n\n"
        "Send any message to start chatting.\n\n"
        "/skills — review pending skills\n"
        "/memory — show memory\n"
        "/clear  — fresh conversation\n"
        "/status — agent status"
    )


async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = os.getenv("TELEGRAM_CHAT_ID")
    if target and str(chat_id) != str(target):
        return
    try:
        from rexio_agent.core.memory_store import MemoryStore
        store = MemoryStore()
        store.load()
        mem = "\n".join(store.memory_entries) if store.memory_entries else "(empty)"
        usr = "\n".join(store.user_entries) if store.user_entries else "(empty)"
        text = f"🧠 MEMORY:\n{mem}\n\n👤 USER PROFILE:\n{usr}"
        await update.message.reply_text(text[:4000])
    except Exception as e:
        await update.message.reply_text(f"⚠️ Could not load memory: {e}")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = os.getenv("TELEGRAM_CHAT_ID")
    if target and str(chat_id) != str(target):
        return
    conv_id = f"telegram_{chat_id}"
    if conv_id in sessions:
        del sessions[conv_id]
    await update.message.reply_text("🗑 Conversation cleared. Starting fresh!")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target = os.getenv("TELEGRAM_CHAT_ID")
    if target and str(chat_id) != str(target):
        return
    import os as _os
    model = _os.getenv("MODEL_NAME", "unknown")
    provider = _os.getenv("MODEL_PROVIDER", "unknown")
    pending = len(get_pending_skills())
    text = (
        f"✅ RexiO Agent online\n"
        f"🤖 Model: {model}\n"
        f"🔌 Provider: {provider}\n"
        f"⏳ Pending skills: {pending}"
    )
    await update.message.reply_text(text)


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

    # Wire background review callback — sends notification to this chat
    async def _review_notify(msg: str):
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg)
        except Exception:
            pass

    def _sync_callback(msg: str):
        import asyncio as _aio
        try:
            loop = _aio.get_event_loop()
            loop.call_soon_threadsafe(_aio.ensure_future, _review_notify(msg))
        except Exception:
            pass

    session.background_review_callback = _sync_callback

    # Send initial placeholder — plain text (no Markdown to avoid parse errors)
    status_msg = await update.message.reply_text("☤ Thinking...")

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def producer():
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

    completed_steps: list[str] = []
    answer_chunks: list[str] = []
    last_edit = ""

    async def safe_edit(text: str, use_markdown: bool = False):
        """Edit status message. Plain text by default to avoid Markdown parse errors."""
        nonlocal last_edit
        if not text or text == last_edit:
            return
        try:
            kwargs = dict(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=text,
                disable_web_page_preview=True,
            )
            if use_markdown:
                kwargs["parse_mode"] = "Markdown"
            await context.bot.edit_message_text(**kwargs)
            last_edit = text
        except Exception as e:
            # If Markdown fails, retry as plain text
            if use_markdown:
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_msg.message_id,
                        text=text,
                        disable_web_page_preview=True,
                    )
                    last_edit = text
                except Exception:
                    pass

    def build_status(current_action: str = "") -> str:
        parts = list(completed_steps)
        if current_action:
            parts.append(current_action)
        return "\n".join(parts) if parts else "☤ Thinking..."

    async def keep_typing():
        try:
            while True:
                await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                await asyncio.sleep(4)
        except asyncio.CancelledError:
            pass

    typing_task = asyncio.ensure_future(keep_typing())
    producer_task = loop.run_in_executor(None, producer)

    current_action = ""

    try:
        while True:
            event = await queue.get()

            if event["type"] == "__done__":
                break

            elif event["type"] == "thinking":
                label = tool_label(event.get("tool", ""), event.get("args", ""))
                current_action = f"⏳ {label}..."
                await safe_edit(build_status(current_action=current_action))

            elif event["type"] == "step":
                label = tool_label(event.get("tool", ""), event.get("args", ""))
                completed_steps.append(f"✅ {label}")
                current_action = ""
                await safe_edit(build_status())

            elif event["type"] == "token":
                answer_chunks.append(event["text"])
                if len(answer_chunks) % 10 == 0:
                    await safe_edit("".join(answer_chunks))

            elif event["type"] == "error":
                await safe_edit(f"⚠️ {event.get('message', 'Unknown error')}")
                return

        # Final answer — strip any leaked "Final Answer:" prefix, try Markdown, fallback to plain
        import re as _re
        final = "".join(answer_chunks).strip()
        final = _re.sub(r'^Final Answer:\s*', '', final, flags=_re.IGNORECASE).strip()
        if final:
            await safe_edit(final, use_markdown=True)

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

    application.add_handler(CommandHandler("start",  start_command))
    application.add_handler(CommandHandler("skills", skills_command))
    application.add_handler(CommandHandler("memory", memory_command))
    application.add_handler(CommandHandler("clear",  clear_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CallbackQueryHandler(skill_callback, pattern=r"^skill_(approve|reject):"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await application.initialize()
    await application.start()

    # Register slash command menu in Telegram
    try:
        bot_commands = [BotCommand(name, desc) for name, desc in BOT_COMMANDS]
        await application.bot.set_my_commands(bot_commands)
        logger.info("Telegram bot commands menu set (%d commands)", len(bot_commands))
    except Exception as e:
        logger.warning("Could not set bot commands: %s", e)

    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    logger.info("Telegram Gateway is online and polling for updates.")

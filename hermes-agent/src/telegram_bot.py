import logging

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from . import agent_core, config

logger = logging.getLogger(__name__)


def _is_allowed(user_id: int) -> bool:
    return not config.TELEGRAM_ALLOWED_USER_IDS or user_id in config.TELEGRAM_ALLOWED_USER_IDS


async def _on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not _is_allowed(user_id):
        logger.warning("허용되지 않은 사용자 접근 시도: %s", user_id)
        return

    await update.message.chat.send_action("typing")
    reply = agent_core.run_turn(user_id, update.message.text)
    await update.message.reply_text(reply or "(응답 없음)")


def build_application() -> Application:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _on_message))
    return app


async def send_message(app: Application, chat_id: int, text: str):
    """스케줄러 등 외부 트리거가 사용자에게 선제적으로 메시지를 보낼 때 사용."""
    await app.bot.send_message(chat_id=chat_id, text=text)

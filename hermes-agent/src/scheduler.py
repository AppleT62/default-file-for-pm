import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import Application

from . import agent_core, config
from .jobs import JOBS

logger = logging.getLogger(__name__)


def start_scheduler(app: Application) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)

    for cron_expr, chat_id, prompt in JOBS:
        scheduler.add_job(
            _run_job,
            CronTrigger.from_crontab(cron_expr, timezone=config.TIMEZONE),
            args=[app, chat_id, prompt],
        )

    scheduler.start()
    logger.info("스케줄러 시작: %d개 작업 등록", len(JOBS))
    return scheduler


async def _run_job(app: Application, chat_id: int, prompt: str):
    try:
        reply = agent_core.run_turn(chat_id, prompt)
        await app.bot.send_message(chat_id=chat_id, text=reply or "(응답 없음)")
    except Exception:
        logger.exception("예약 작업 실행 실패: chat_id=%s", chat_id)

import logging

from . import memory
from .scheduler import start_scheduler
from .telegram_bot import build_application

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    memory.init_db()
    app = build_application()
    app.post_init = _on_startup
    app.run_polling()


async def _on_startup(app):
    start_scheduler(app)


if __name__ == "__main__":
    main()

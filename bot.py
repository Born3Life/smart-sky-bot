from __future__ import annotations

import asyncio
import logging
import os
import sys
from os import getenv
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web
from dotenv import load_dotenv

from config import bot_token, telegram_proxy
from database import init_db_async
from handlers import routers

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def _health_handler(_request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def _health_server(port: int) -> None:
    app = web.Application()
    app.router.add_get("/health", _health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("health server on port %d", port)
    await asyncio.Event().wait()


async def main() -> None:
    port = getenv("PORT")
    if port:
        asyncio.create_task(_health_server(int(port)))

    proxy = telegram_proxy()
    if proxy:
        os.environ["HTTP_PROXY"] = proxy
        os.environ["HTTPS_PROXY"] = proxy

    bot = Bot(
        token=bot_token(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    for router in routers:
        dp.include_router(router)

    await init_db_async()
    logger.info("SmartSkyBot started")
    await dp.start_polling(bot, polling_timeout=1)


if __name__ == "__main__":
    asyncio.run(main())

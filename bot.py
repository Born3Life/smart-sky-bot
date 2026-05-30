from __future__ import annotations

import asyncio
import logging
import sys
from os import getenv
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from aiogram.exceptions import TelegramConflictError, TelegramNetworkError, TelegramRetryAfter
from dotenv import load_dotenv

from config import bot_token, telegram_proxy
from database import init_db_async
from handlers import routers
from middleware.onboarding import OnboardingMiddleware
from middleware.premium import PremiumMiddleware
from services.weather_monitor import _init_cache_table, check_and_notify, morning_briefing

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


async def _weather_monitor_loop(bot: Bot) -> None:
    await asyncio.sleep(1800)
    while True:
        try:
            await morning_briefing(bot)
            await check_and_notify(bot)
            logger.info("weather monitor cycle done")
        except Exception:
            logger.exception("weather monitor error")
        await asyncio.sleep(3600)


async def main() -> None:
    port = getenv("PORT")
    if port:
        asyncio.create_task(_health_server(int(port)))

    proxy = telegram_proxy()
    session = AiohttpSession(proxy=proxy) if proxy else AiohttpSession()

    bot = Bot(
        token=bot_token(),
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(OnboardingMiddleware())
    dp.message.middleware(PremiumMiddleware())

    for router in routers:
        dp.include_router(router)

    await init_db_async()
    _init_cache_table()
    asyncio.create_task(_weather_monitor_loop(bot))
    logger.info("SmartSkyBot started")

    await bot.delete_webhook(drop_pending_updates=True)

    while True:
        try:
            await dp.start_polling(bot, polling_timeout=1)
        except TelegramConflictError as e:
            logger.warning("Conflict — another bot instance is running: %s — retry in 30s", e)
            await asyncio.sleep(30)
        except (TelegramNetworkError, TelegramRetryAfter) as e:
            logger.warning("Telegram connection error: %s — retry in 10s", e)
            await asyncio.sleep(10)
        except Exception:
            logger.exception("Fatal polling error — retry in 30s")
            await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())

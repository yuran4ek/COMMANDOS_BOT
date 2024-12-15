import asyncio

from aiogram import (
    Bot,
    Dispatcher
)

from config.config import BOT_TOKEN


async def main():

    bot = Bot(
        token=BOT_TOKEN,
        parse_mode='HTML'
    )
    dp = Dispatcher()

    await set_main_menu()

    dp.include_router()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())

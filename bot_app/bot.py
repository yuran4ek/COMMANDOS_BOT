import asyncio

from aiogram import (
    Bot,
    Dispatcher
)
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode

from bot_app.filters.transliterate_filter import TransliterationFilter
from bot_app.middlewares.add_pool_in_handlers import DatabaseMiddleware
from bot_app.handlers.bot_commands import bot_commands_router
from bot_app.handlers.group_handlers import bot_group_joined_router
from bot_app.handlers.user_handlers import bot_user_handlers_router
from bot_app.handlers.admin_handlers import bot_admins_handlers_router
from bot_app.keyboards.bot_menu import set_main_menu

from config.config import BOT_TOKEN
from config.database import (
    create_pool,
    close_pool
)
from config.log import logger


async def main():

    """

    :return:
    """

    # Инициализируем pool и bot перед try, чтобы можно было закрыть его в finally
    pool = None
    bot = None

    try:
        # Создание пулла подключений к БД
        pool = await create_pool()

        # Инициализация бота
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        dp = Dispatcher()

        dp.update.middleware(DatabaseMiddleware(pool=pool))

        # Сохраняем объект Bot в Dispatcher
        dp['bot'] = bot

        # Регистрация кнопки menu
        await set_main_menu(bot)

        # bot_admins_handlers_router.message.filter(TransliterationFilter())
        # bot_user_handlers_router.message.filter(TransliterationFilter())

        # Регистрация хендлеров
        dp.include_router(bot_commands_router)
        dp.include_router(bot_admins_handlers_router)
        dp.include_router(bot_user_handlers_router)
        dp.include_router(bot_group_joined_router)

        # Запуск бота
        await bot.delete_webhook(drop_pending_updates=True)

        print('Успешный запуск бота!')
        logger.info('Успешный запуск бота!')

        await dp.start_polling(bot)

    except asyncio.CancelledError:
        logger.info('Остановка бота...')
    finally:
        logger.info('Бот завершает работу...')

        # Закрываем сессию бота, если он был создан
        if bot:
            await bot.session.close()

        # Закрываем пул соединений с БД, если он был создан
        if pool:
            await close_pool(pool)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Бот остановлен вручную!')

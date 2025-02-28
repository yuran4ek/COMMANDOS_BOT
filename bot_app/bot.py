import asyncio

from aiogram import (
    Bot,
    Dispatcher
)

from handlers.bot_commands import bot_commands_router
from handlers.group_handlers import bot_group_joined_router
from handlers.user_handlers import bot_user_handlers_router
from handlers.admin_handlers import bot_admins_handlers_router
from keyboards.bot_menu import set_main_menu

from config.config import BOT_TOKEN
from config.database import (
    create_pool,
    close_pool
)


async def main():

    # Создание пулла подключений к БД
    pool = await create_pool()

    # Инициализация бота
    bot = Bot(
        token=BOT_TOKEN,
        parse_mode='HTML'
    )
    dp = Dispatcher()

    # Сохраняем объект Bot в Dispatcher
    dp['bot'] = bot

    # Передача пула в роутеры
    bot_commands_router.message.middleware(lambda handler, data: {'pool': pool})
    bot_group_joined_router.message.middleware(lambda handler, data: {'pool': pool})
    bot_user_handlers_router.message.middleware(lambda handler, data: {'pool': pool})
    bot_admins_handlers_router.message.middleware(lambda handler, data: {'pool': pool})

    # Регистрация кнопки menu
    await set_main_menu(bot)

    # Регистрация хендлеров
    dp.include_router(bot_commands_router)
    dp.include_router(bot_group_joined_router)
    dp.include_router(bot_user_handlers_router)
    dp.include_router(bot_admins_handlers_router)

    # Запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

    # Закрытие пула после завершения работы бота
    await close_pool(pool)


if __name__ == '__main__':
    asyncio.run(main())

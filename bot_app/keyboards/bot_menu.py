from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeAllGroupChats
)


from bot_app.lexicon.lexicon_common.lexicon_ru import MENU_COMMANDS


async def set_main_menu(bot: Bot):

    """
    Создание кнопок меню для бота.
    :param bot: Объект Bot.
    :return: Функция ничего не возвращает.
    """

    # Создаём кнопку меню с командами
    main_menu_commands = [
        BotCommand(
            command=command,
            description=description
        )
        for command, description in MENU_COMMANDS.items()
    ]

    # Создаём меню в боте
    await bot.set_my_commands(
        main_menu_commands,
        scope=BotCommandScopeAllPrivateChats()
    )

    # Удаляем команды для групп и супергрупп
    await bot.set_my_commands(
        [],
        scope=BotCommandScopeAllGroupChats()
    )

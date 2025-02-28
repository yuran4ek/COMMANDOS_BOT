import asyncpg
from aiogram import Router, Bot
from aiogram.types import (
    Message,
    ChatMemberUpdated
)
from aiogram.filters import (
    ChatMemberUpdatedFilter,
    IS_NOT_MEMBER,
    IS_MEMBER
)

from bot_app.keyboards.keyboards import create_link_button
from bot_app.lexicon.lexicon_common.lexicon_ru import LEXICON_RU

from config.database import (
    add_group_to_db,
    delete_group_from_db
)
from config.log import logger


# Создаём роутер для всех хендлеров, связанных с взаимодействием бота с группами
bot_group_joined_router = Router(name='bot_group_joined_router')


@bot_group_joined_router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_chat_joined(event: ChatMemberUpdated,
                         pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий на событие добавления бота в группу.
    :param event: Событие ChatMemberUpdated.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Получаем данные о чате и группе
        chat = event.chat
        group_id = chat.id
        group_name = chat.title

        try:
            # Добавляем группу в БД
            await add_group_to_db(
                pool=pool,
                group_id=group_id,
                group_name=group_name
            )
            logger.info(f'Группа {group_name} с ID {group_id} была добавлена в БД.')
            # Уведомляем пользователей в группе о том, что они могут взаимодействовать с ботом
            await event.bot.send_message(
                chat_id=group_id,
                text=LEXICON_RU['hello_group_join'],
                reply_markup=create_link_button()
            )
        except Exception as e:
            logger.error(f'Ошибка при отправке приветственного сообщения в группу: {e}')
    except Exception as e:
        logger.error(f'Неожиданная ошибка в обработчике ChatMemberUpdatedFilter: {e}')


@bot_group_joined_router.message()
async def on_bot_mention(message: Message,
                         bot: Bot):

    """
    Хендлер, срабатывающий на упоминание бота в группе.
    :param message: Сообщение от пользователя.
    :param bot: Объект Bot.
    :return: Функция ничего не возвращает.
    """

    try:
        # Получаем информацию о боте
        bot_info = await bot.get_me()

        # Проверяем, есть ли упоминание бота в сообщении
        if f'@{bot_info.username}' in message.text.split():
            # Отправляем сообщение с инлайн-кнопкой для перехода в ЛС
            await message.reply(
                text=LEXICON_RU['private_message'],
                reply_markup=create_link_button()
            )
    except Exception as e:
        logger.error(f'Ошибка в обработчике упоминания бота: {e}')
        await message.answer(LEXICON_RU['error'])


@bot_group_joined_router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_chat_member_updated(event: ChatMemberUpdated,
                                 pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий на событие, когда изменяется статус бота в группе.
    :param event: Объект для слежения за статусом в группе.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Проверяем изменение статуса бота в группе
        if event.new_chat_member.user.id == event.bot.id and event.new_chat_member.status in ['left', 'kicked']:
            # Получаем данные о группе
            group_id = event.chat.id
            group_name = event.chat.title

            # Удаляем группу из БД
            await delete_group_from_db(
                pool=pool,
                group_id=group_id
            )
            logger.info(f'Группа {group_name} с ID {group_id} была удалена из БД.')
    except Exception as e:
        logger.error(f'Неожиданная ошибка при удалении бота из группы: {e}')

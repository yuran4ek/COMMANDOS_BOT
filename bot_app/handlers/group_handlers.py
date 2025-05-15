import asyncpg
from aiogram import (
    Router,
    Bot,
    F
)
from aiogram.types import (
    Message,
    ChatMemberUpdated
)
from aiogram.filters import (
    ChatMemberUpdatedFilter,
    IS_NOT_MEMBER,
    IS_MEMBER,
    ADMINISTRATOR,
    JOIN_TRANSITION
)

from bot_app.exceptions.database import (
    DatabaseAddGroupError,
    DatabaseDeleteGroupError
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


@bot_group_joined_router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_chat_joined(event: ChatMemberUpdated):

    """
    Хендлер, срабатывающий на событие добавления бота в группу.
    :param event: Событие ChatMemberUpdated.
    :return: Функция ничего не возвращает.
    """

    try:
        # Получаем данные о чате и группе
        chat = event.chat
        group_id = chat.id
        group_name = chat.title if chat.title else f'Группа без имени ({group_id})'

        logger.info(f'Бот был добавлен в группу {group_name} с ID {group_id}.')

        chat_info = await event.bot.get_chat(chat_id=group_id)

        if chat_info.permissions.can_send_messages:
            await event.bot.send_message(
                chat_id=group_id,
                text=LEXICON_RU['add_bot_in_group']
            )
        else:
            logger.warning(f'Бот пока не имеет прав на отправку сообщений в группе {group_name}.'
                           f'Для отправки сообщений необходимо выдать права администратора боту.')

    except Exception as e:
        logger.error(f'Неожиданная ошибка в обработчике ChatMemberUpdatedFilter: {e}')


@bot_group_joined_router.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> ADMINISTRATOR))
async def on_chat_admin(event: ChatMemberUpdated,
                        pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий на предоставление боту прав админа в группе.
    :param event: Событие ChatMemberUpdated.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Получаем данные о чате и группе
        chat = event.chat
        group_id = chat.id
        group_name = chat.title if chat.title else f'Группа без имени ({group_id})'
        try:
            # Добавляем группу в БД
            await add_group_to_db(
                pool=pool,
                group_id=group_id,
                group_name=group_name
            )
            logger.info(f'Группа {group_name} с ID {group_id} была добавлена в БД.')
            # Уведомляем пользователей в группе о том, что они могут взаимодействовать с ботом
            await event.answer(
                text=LEXICON_RU['hello_group_join'],
                reply_markup=create_link_button()
            )
        except DatabaseAddGroupError as e:
            logger.error(e)
        except Exception as e:
            logger.error(f'Ошибка при отправке приветственного сообщения в группу: {e}')
    except Exception as e:
        logger.error(f'Неожиданная ошибка в обработчике ChatMemberUpdatedFilter: {e}')


@bot_group_joined_router.message(F.text)
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

        if message.entities:
            for entity in message.entities:
                if entity.type == 'mention':
                    mention_text = message.text[entity.offset : entity.offset + entity.length]
                    # Проверяем, есть ли упоминание бота в сообщении
                    if mention_text == f'@{bot_info.username}':
                        # Отправляем сообщение с инлайн-кнопкой для перехода в ЛС
                        await message.reply(
                            text=LEXICON_RU['private_message'],
                            reply_markup=create_link_button()
                        )
    except Exception as e:
        logger.error(f'Ошибка в обработчике упоминания бота: {e}')
        await message.answer(LEXICON_RU['error'])


@bot_group_joined_router.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
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
    except DatabaseDeleteGroupError as e:
        logger.error(e)
    except Exception as e:
        logger.error(f'Неожиданная ошибка при удалении бота из группы: {e}')

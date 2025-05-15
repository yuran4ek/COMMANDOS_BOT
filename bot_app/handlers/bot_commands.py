import asyncpg.pool

from aiogram import (
    Bot,
    Router,
    types
)
from aiogram import filters
from aiogram.fsm.context import FSMContext

from bot_app.exceptions.database import (
    DatabaseGetCategoriesError,
    DatabaseGetGroupError
)
from bot_app.filters.check_chat_type import ChatTypeFilter
from bot_app.keyboards.keyboards import (
    create_categories_keyboard,
    create_link_chanel_button
)
from bot_app.lexicon.lexicon_common.lexicon_ru import LEXICON_RU
from bot_app.utils.admin_check import check_is_admin

from config.database import (
    get_groups_from_db,
    get_categories_from_db
)
from config.log import logger


# Создаём роутер для всех хендлеров, связанных с командами для бота
bot_commands_router = Router(name='bot_commands_router')


@bot_commands_router.message(ChatTypeFilter('private'),
                             filters.Command('cancel'))
async def cancel_handler(message: types.Message,
                         state: FSMContext):

    """
    Хендлер, срабатывающий на команду /cancel.
    :param message: Сообщение от пользователя с командой /cancel.
    :param state: Состояние пользователя для FSM.
    :return: Функция ничего не возвращает.
    """

    try:
        # Отправляем пользователю сообщение об отмене действия
        await message.answer(text=LEXICON_RU['cancel'])
        # Очищаем состояние для дальнейшего его использования
        await state.clear()
        # Устанавливаем флаг True для сброса кнопок
        await state.update_data(cancel_handler=True)
    except Exception as e:
        logger.error(f'Ошибка в обработке команды /cancel: {e}')
        await message.answer(LEXICON_RU['error'])


@bot_commands_router.message(ChatTypeFilter('private'),
                             filters.Command('start'))
async def start_command(message: types.Message,
                        bot: Bot,
                        pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий на команду /start с параметрами.
    :param message: Сообщение от пользователя с командой /start.
    :param bot:Объект Bot.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Получаем данные о пользователе
        user_id = message.from_user.id

        # Получаем группы из БД
        groups_id = await get_groups_from_db(pool=pool)
        logger.info(f'Успешное получение всех групп из БД.')

        # Получаем категории из БД
        categories = await get_categories_from_db(pool=pool)
        logger.info(f'Успешное получение всех категорий из БД.')

        category_name = ''
        for name in categories:
            category_name += f'{name.get("name")}\n'

        # Проверяем, является ли пользователь администратором в одной из групп
        is_admin = await check_is_admin(
            bot=bot,
            user_id=user_id,
            groups_id=groups_id
        )

        text = f'{LEXICON_RU["/start"]}\n\n'

        # Если админ
        if is_admin:
            text += f'{LEXICON_RU["info_for_admins"]}\n' \
                    f'{category_name}'

        # Получаем параметр из команды /start
        parameter = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
        if parameter == 'welcome_to_private':
            await message.answer(text=text)
        else:
            await message.answer(text=text)

    except DatabaseGetGroupError as e:
        logger.error(e)
    except DatabaseGetCategoriesError as e:
        logger.error(e)
    except KeyError as e:
        logger.error(f'Ключ {e} отсутствует в LEXICON_RU')
        await message.answer(LEXICON_RU['error_key'])
    except Exception as e:
        logger.error(f'Ошибка в обработке команды /start: {e}')
        await message.answer(LEXICON_RU['error'])


@bot_commands_router.message(ChatTypeFilter('private'),
                             filters.Command('assembl'))
async def assembles_command(message: types.Message,
                            state: FSMContext,
                            pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий на команду /сборки.
    :param message: Сообщение от пользователя с командой сборки.
    :param state: Состояние пользователя для FSM.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Устанавливаем флаг False для активации кнопок
        await state.update_data(cancel_handler=False)
        # Получаем категории из БД
        categories = await get_categories_from_db(pool=pool)

        keyboard = create_categories_keyboard(categories=categories)

        # Отправляем пользователю кнопки с категориями
        await message.answer(
            text=LEXICON_RU['assembl'],
            reply_markup=keyboard
            )
    except DatabaseGetCategoriesError as e:
        logger.error(e)
        await message.answer(LEXICON_RU['error'])
    except Exception as e:
        logger.error(f'Ошибка в обработке команды /assembl: {e}')
        await message.answer(LEXICON_RU['error'])


@bot_commands_router.message(ChatTypeFilter('private'),
                             filters.Command('help'))
async def help_command(message: types.Message,
                       bot: Bot,
                       pool: asyncpg.pool.Pool
                       ):

    """
    Хендлер, срабатывающий на команду /help.
    :param message: Сообщение от пользователя с командой сборки.
    :param bot: Объект Bot.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Получаем данные о пользователе
        user_id = message.from_user.id

        # Получаем группы из БД
        groups_id = await get_groups_from_db(pool=pool)
        logger.info(f'Успешное получение всех групп из БД.')

        # Получаем категории из БД
        categories = await get_categories_from_db(pool=pool)
        logger.info(f'Успешное получение всех категорий из БД.')

        category_name = ''
        for name in categories:
            category_name += f'🔹 {name.get("name")} - {name.get("description")}\n'

        # Проверяем, является ли пользователь администратором в одной из групп
        is_admin = await check_is_admin(
            bot=bot,
            user_id=user_id,
            groups_id=groups_id
        )

        text = f'{LEXICON_RU["/help"]}\n\n'

        # Если админ
        if is_admin:
            text += f'{LEXICON_RU["info_for_admins"]}\n' \
                    f'{category_name}'

        # Отправляем пользователю сообщение с помощью
        await message.answer(text=text)

    except DatabaseGetGroupError as e:
        logger.error(e)
        await message.answer(LEXICON_RU['error'])
    except DatabaseGetCategoriesError as e:
        logger.error(e)
        await message.answer(LEXICON_RU['error'])
    except Exception as e:
        logger.error(f'Ошибка в обработке команды /help: {e}')
        await message.answer(LEXICON_RU['error'])


@bot_commands_router.message(ChatTypeFilter('private'),
                             filters.Command('commandos'))
async def cancel_handler(message: types.Message):

    """
    Хендлер, срабатывающий на команду /COMMANDOS.
    :param message: Сообщение от пользователя с командой /COMMANDOS.
    :return: Функция ничего не возвращает.
    """

    try:
        # Отправляем пользователю сообщение об отмене действия
        await message.answer(
            text=LEXICON_RU['text_for_url_for_chanel'],
            reply_markup=create_link_chanel_button()
        )
    except Exception as e:
        logger.error(f'Ошибка в обработке команды /COMMANDOS: {e}')
        await message.answer(LEXICON_RU['error'])

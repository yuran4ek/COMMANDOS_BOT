import asyncpg.pool
from aiogram import (
    Router,
    types
)
from aiogram import filters
from aiogram.fsm.context import FSMContext

from bot_app.keyboards.keyboards import create_categories_keyboard
from bot_app.lexicon.lexicon_common.lexicon_ru import LEXICON_RU
from bot_app.states.user_states import SelectFromUserState

from config.database import get_categories_from_db
from config.log import logger


# Создаём роутер для всех хендлеров, связанных с командами для бота
bot_commands_router = Router(name='bot_commands_router')


@bot_commands_router.message(filters.Command('cancel'))
async def cancel_handler(message: types.Message,
                         state: FSMContext):

    """
    Хендлер, срабатывающий на команду /cancel.
    :param message: Сообщение от пользователя с командой /cancel.
    :param state: Состояние пользователя для FSM.
    :return: Функция ничего не возвращает.
    """

    try:
        # Получаем актуальное состояние из FSM
        current_state = await state.get_state()
        # Проверяем, если в состоянии ничего нет, то ничего не делаем
        if current_state is None:
            return None
        # Отправляем пользователю сообщение об отмене действия
        await message.answer(text=LEXICON_RU['cancel'])
        # Очищаем состояние для дальнейшего его использования
        await state.clear()
    except Exception as e:
        logger.error(f'Ошибка в обработке команды /cancel: {e}')
        await message.answer(LEXICON_RU['error'])


@bot_commands_router.message(filters.Command('start'))
async def start_command(message: types.Message):

    """
    Хендлер, срабатывающий на команду /start с параметрами.
    :param message: Сообщение от пользователя с командой /start.
    :return: Функция ничего не возвращает.
    """

    try:
        # Получаем параметр из команды /start
        parameter = message.get_args()
        if parameter == 'welcome_to_private':
            await message.answer(text=LEXICON_RU['/start'])
        else:
            await message.answer(text=LEXICON_RU['/start'])
    except KeyError as e:
        logger.error(f'Ключ {e} отсутствует в LEXICON_RU')
        await message.answer(LEXICON_RU['error_key'])
    except Exception as e:
        logger.error(f'Ошибка в обработке команды /start: {e}')
        await message.answer(LEXICON_RU['error'])


@bot_commands_router.message(filters.Command('сборки'))
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
        # Получаем категории из БД
        category_name = await get_categories_from_db(pool=pool)
        # Отправляем пользователю кнопки с категориями
        await message.answer(
            text=LEXICON_RU['сборки'],
            reply_markup=create_categories_keyboard(category_name)
        )
        # Переходим в состояния выбора категории пользователем
        await state.set_state(SelectFromUserState.category)
    except Exception as e:
        logger.error(f'Ошибка в обработке команды /сборки: {e}')
        await message.answer(LEXICON_RU['error'])

import pytest
import pytest_asyncio

from typing import (
    Callable,
    Awaitable
)

from unittest.mock import (
    AsyncMock,
    MagicMock
)


from aiogram import Bot
from aiogram.types import (
    Message,
    Chat,
    User,
    ChatMemberUpdated,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from aiogram.fsm.context import FSMContext


@pytest_asyncio.fixture
async def mock_db_pool() -> Callable[[dict], Awaitable[tuple[MagicMock, MagicMock]]]:

    """
    Фикстура для мокирования пула соединения и само соединение с БД.
    :return: Возвращает функцию, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    """

    async def _mock_db_pool(data: dict) -> tuple[MagicMock, MagicMock]:
        # Мокаем пул соединений и само соединение
        mock_pool = MagicMock()
        mock_conn = MagicMock()

        # Настраиваем поведение acquire() для работы с контекстным менеджером
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Настройка поведения transaction
        mock_conn.transaction.return_value.__aenter__.return_value = mock_conn

        # Мокируем fetch, чтобы он возвращал значение через асинхронную обертку
        async def mock_fetch(*args, **kwargs):
            return data

        # Мокируем fetchval, чтобы он возвращал значение через асинхронную обертку
        async def mock_fetchval(*args, **kwargs):
            return data

        # Мокируем fetchrow, чтобы он возвращал значение через асинхронную обертку
        async def mock_fetchrow(*args, **kwargs):
            return data

        # Мокируем поведение fetch, fetchval и fetchrow
        mock_conn.fetch = MagicMock(side_effect=mock_fetch)
        mock_conn.fetchval = MagicMock(side_effect=mock_fetchval)
        mock_conn.fetchrow = MagicMock(side_effect=mock_fetchrow)

        # Настраиваем метод execute как асинхронный
        mock_conn.execute = AsyncMock()

        return mock_pool, mock_conn

    return _mock_db_pool


@pytest_asyncio.fixture
def mock_handler(mocker):

    """
    Фикстура для мокирования хендлеров.
    :param mocker: Мокер.
    :return: Возвращает замокированные объекты message, state и callback.
    """

    # Мокируем Message
    message = mocker.Mock(spec=Message)
    message.answer = AsyncMock()
    message.answer_photo = AsyncMock()
    message.edit_text = AsyncMock()
    message.edit_caption = AsyncMock()
    message.reply = AsyncMock()

    # Мокируем CallbackQuery
    callback = mocker.Mock(spec=CallbackQuery)
    callback.answer = AsyncMock()
    callback.message = message
    callback.message.delete = AsyncMock()

    # Мокируем photo
    message.photo = [mocker.Mock()]

    # Мокируем user
    message.from_user = mocker.Mock()
    callback.from_user = mocker.Mock()

    # Мокируем FSMContext
    state = mocker.Mock(spec=FSMContext)
    state.set_state = AsyncMock()
    state.get_data = AsyncMock()
    state.clear = AsyncMock()

    return message, callback, state


@pytest.fixture
def mock_group_handler(mocker):

    """
    Фикстура для мокирования хендлеров для отслеживания взаимодействий бота в группе.
    :param mocker: Мокер.
    :return: Возвращает замокированные объекты event.
    """

    # Мокируем Chat
    chat = mocker.Mock(spec=Chat)

    # Мокируем User
    user = mocker.Mock(spec=User)

    # Мокируем Bot
    bot = mocker.Mock(spec=Bot)
    bot.get_me = AsyncMock(return_value=bot)

    # Мокируем ChatMemberUpdated
    event = mocker.Mock(spec=ChatMemberUpdated)
    event.chat = chat
    event.new_chat_member = user
    event.new_chat_member.user = user
    event.bot = mocker.Mock()
    event.bot.send_message = AsyncMock()

    return bot, event


@pytest.fixture
def mock_admin():

    """
    Фикстура для мокирования Dispatcher, bot и get_chat_member.
    :return: Возвращает замокированные объекты mock_dp, mock_bot и mock_member.
    """

    # Мокируем объект Dispatcher и bot
    mock_dp = AsyncMock()
    mock_bot = AsyncMock()
    mock_dp.__getitem__.return_value = mock_bot

    # Мокируем метод get_chat_member
    mock_member = AsyncMock()
    mock_bot.get_chat_member = AsyncMock(return_value=mock_member)

    return mock_dp, mock_bot, mock_member


@pytest.fixture
def keyboards_test_data() -> dict[str, InlineKeyboardMarkup]:

    """
    Фикстура для мокирования клавиатур.
    :return: Возвращает словарь, состоящий из строк и объектов InlineKeyboardMarkup.
    """

    return {
        'link_button': InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text='Перейти в ЛС',
                        callback_data='https://t.me/test_bot?start=welcome_to_private'
                    )
                ]
            ]
        ),
        'pagination_keyboard': InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text='◀',
                        callback_data='page_1'
                    ),
                    InlineKeyboardButton(
                        text='1/1',
                        callback_data='page_info'
                    ),
                    InlineKeyboardButton(
                        text='▶',
                        callback_data='page_2'
                    )
                ],
                [
                    InlineKeyboardButton(
                        text='Поиск фото',
                        callback_data='search_photo'
                    )
                ]
            ]
        ),
        'admin_keyboard': InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text='Удалить фото',
                        callback_data='delete_photo'
                    ),
                    InlineKeyboardButton(
                        text='Изменить описание',
                        callback_data='update_description'
                    )
                ]
            ]
        ),
        'confirmation_keyboard': InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text='Да',
                        callback_data='confirm_test_yes'
                    ),
                    InlineKeyboardButton(
                        text='Нет',
                        callback_data='confirm_test_no'
                    )
                ]
            ]
        )
    }


@pytest.fixture
def sample_test_data() -> dict[str, dict[str, str | int] | list[int] | list[dict[str, int]] | str]:

    """
    Фикстура с данными для тестов.
    :return: Возвращает словарь с данными для тестов.
    """

    return {
        'user': {
            'user_id': 123
        },
        'group': {
            'group_id': 123,
            'group_name': 'Test Group'
        },
        'groups': [
            123,
            456,
            789
        ],
        'photo': {
            'photo_id': 'AgACAgIAAxkBAAEB12345ExampleFileIDExampleID12345',
            'description': 'Description123',
            'category': 'Category123',
            'new_description': 'NewDescription'
        },
        'photos': [
            {
                'photo_id': 'AgACAgIAAxkBAAEB12345ExampleFileIDExampleID12345',
                'description': 'Description123',
                'category': 'Category123'
            },
            {
                'photo_id': 'photo456',
                'description': 'Description456',
                'category': 'Category123'
            },
            {
                'photo_id': 'photo789',
                'description': 'Description789',
                'category': 'Category'
            }
        ],
        'category': [
            'Category123',
            'Category456',
            'Category789'
        ],
        'state': {
            'photo_id': 'AgACAgIAAxkBAAEB12345ExampleFileIDExampleID12345',
            'category': 'Category123',
            'new_description': 'NewDescription',
            'current_page': 2
        },
        'text': {
            'text': 'Некоторый текст',
            'transliterated_text': 'Nekotory tekst'
        },
        'command': [
            'add',
            'delete',
            'update'
        ],
        'chat': {
            'chat_id': 123456789,
            'chat_title': 'Test Group',
            'bot_id': 987654321
        },
        'bot': 'TestBot'
    }

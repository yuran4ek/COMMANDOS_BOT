import pytest

from unittest.mock import AsyncMock

from bot_app.handlers.group_handlers import (
    on_chat_joined,
    on_bot_mention,
    on_chat_member_updated
)
from bot_app.lexicon.lexicon_common.lexicon_ru import LEXICON_RU


@pytest.mark.asyncio
async def test_on_chat_joined(mock_db_pool,
                              mock_group_handler,
                              sample_test_data,
                              keyboards_test_data,
                              mocker):

    """
    Тестирование хендлера для события добавления бота в группу.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param mock_group_handler: Функция, возвращающая замокированный объект для ChatMemberUpdated в виде event
    и замокированный объект bot.
    :param sample_test_data: Словарь с тестовыми данными.
    :param mocker: Мокер для добавления side_effect в тест для тестирования ошибки.
    :return: Функция ничего не возвращает.
    """

    # Данные для теста
    chat_data = sample_test_data['chat']
    chat_id = chat_data['chat_id']
    chat_title = chat_data['chat_title']
    bot_id = chat_data['bot_id']

    keyboard_link_button = keyboards_test_data['link_button']

    # Мокаем функции для работы с БД
    mock_add_group_to_db = mocker.patch(
        'bot_app.handlers.group_handlers.add_group_to_db',
        return_value=None
    )

    # Мокаем функцию создания клавиатуры
    mock_create_link_button = mocker.patch(
        'bot_app.handlers.group_handlers.create_link_button',
        return_value=keyboard_link_button
    )

    # Получаем данные из наших фикстур
    mock_pool, mock_conn = await mock_db_pool(data=chat_id)
    bot, event = mock_group_handler

    event.chat.id = chat_id
    event.chat.title = chat_title
    event.new_chat_member.id = bot_id
    event.new_chat_member.is_bot = True

    # Запуск хендлера
    await on_chat_joined(
        event=event,
        pool=mock_pool
    )

    # Проверяем, что функция для получения фото была вызвана с правильными параметрами
    mock_add_group_to_db.assert_called_once_with(
        pool=mock_pool,
        group_id=chat_id,
        group_name=chat_title
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_link_button.assert_called_once()

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    event.bot.send_message.assert_called_once_with(
        chat_id=event.chat.id,
        text=LEXICON_RU['hello_group_join'],
        reply_markup=keyboard_link_button
    )

    # Тестируем сценарий с ошибкой
    mock_add_group_to_db.side_effect = Exception("Test error")
    event.bot.send_message.reset_mock()

    # Запуск хендлера
    await on_chat_joined(
        event=event,
        pool=mock_pool
    )


@pytest.mark.asyncio
async def test_on_bot_mention(mock_handler,
                              mock_group_handler,
                              sample_test_data,
                              keyboards_test_data,
                              mocker):

    """
    Тестирование хендлера для события упоминания бота в группе.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :param mock_group_handler: Функция, возвращающая замокированный объект для ChatMemberUpdated в виде event.
    :param sample_test_data: Словарь с тестовыми данными.
    :param keyboards_test_data: .
    :param mocker: Мокер для добавления side_effect в тест для тестирования ошибки.
    :return: Функция ничего не возвращает.
    """

    # Данные для теста
    bot_name = sample_test_data['bot']

    keyboard_link_button = keyboards_test_data['link_button']

    # Мокаем функцию создания клавиатуры
    mock_create_link_button = mocker.patch(
        'bot_app.handlers.group_handlers.create_link_button',
        return_value=keyboard_link_button
    )

    # Получаем данные из наших фикстур
    message, _, _ = mock_handler
    bot, event = mock_group_handler

    bot.username = bot_name
    message.text = f'@{bot_name} Привет!'

    # Запуск хендлера
    await on_bot_mention(
        message=message,
        bot=bot
    )

    bot.get_me.assert_called_once()

    message.reply.assert_called_once_with(
        text=LEXICON_RU['private_message'],
        reply_markup=keyboard_link_button
    )

    mock_create_link_button.assert_called_once()

    # Тестируем сценарий с ошибкой
    bot.get_me.side_effect = Exception("Test error")

    # Запуск хендлера
    await on_bot_mention(
        message=message,
        bot=bot
    )

    message.answer.assert_called_once_with(LEXICON_RU['error'])


@pytest.mark.asyncio
async def test_on_chat_member_updated(mock_db_pool,
                                      mock_group_handler,
                                      sample_test_data,
                                      mocker):

    """
    Тестирование хендлера для события удаления бота из группы.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param mock_group_handler: Функция, возвращающая замокированный объект для ChatMemberUpdated в виде event.
    :param sample_test_data: Словарь с тестовыми данными.
    :param mocker: Мокер для добавления side_effect в тест для тестирования ошибки.
    :return: Функция ничего не возвращает.
    """

    # Данные для теста
    chat_data = sample_test_data['chat']
    chat_id = chat_data['chat_id']
    chat_title = chat_data['chat_title']
    bot_id = chat_data['bot_id']

    # Мокаем функции для работы с БД
    mock_delete_group_from_db = mocker.patch(
        'bot_app.handlers.group_handlers.delete_group_from_db',
        return_value=None
    )

    # Получаем данные из наших фикстур
    mock_pool, mock_conn = await mock_db_pool(data=chat_id)
    bot, event = mock_group_handler

    event.chat.id = chat_id
    event.chat.title = chat_title
    event.bot.id = bot_id
    event.new_chat_member.user.id = bot_id
    event.new_chat_member.status = 'kicked'

    # Запуск хендлера
    await on_chat_member_updated(
        event=event,
        pool=mock_pool
    )

    # Проверяем, что функция удаления группы из БД была вызвана с правильными параметрами
    mock_delete_group_from_db.assert_called_once_with(
        pool=mock_pool,
        group_id=chat_id
    )

    # Тестируем сценарий с ошибкой
    mock_delete_group_from_db.side_effect = Exception("Test error")

    # Запуск хендлера
    await on_chat_member_updated(
        event=event,
        pool=mock_pool
    )

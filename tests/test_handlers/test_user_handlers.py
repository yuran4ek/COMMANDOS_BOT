import pytest

from unittest.mock import AsyncMock

from bot_app.handlers.user_handlers import (
    search_photo_handler,
    search_photo_callback,
    category_selection_callback,
    process_pagination_callback,
    send_photo_handler
)
from bot_app.lexicon.lexicon_common.lexicon_ru import LEXICON_RU
from bot_app.states.user_states import SearchPhotoState


@pytest.mark.asyncio
async def test_search_photo_handler(mock_db_pool,
                                    mock_handler,
                                    sample_test_data,
                                    mocker):

    """
    Тестирование хендлера для поиска фото.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :param sample_test_data: Словарь с тестовыми данными.
    :param mocker: Мокер для добавления side_effect в тест для тестирования ошибки.
    :return: Функция ничего не возвращает.
    """

    photo_data = sample_test_data['photos']
    query = '123'

    # Фильтруем данные, которые содержат '123' в description
    filtered_data = [
        photo for photo in photo_data if query in photo['description']
    ]

    mock_search_photo_by_description_in_db = mocker.patch(
        'bot_app.handlers.user_handlers.search_photo_by_description_in_db',
        return_value=filtered_data
    )

    mock_pool, mock_conn = await mock_db_pool(data=filtered_data)
    message, callback, state = mock_handler

    message.text = query

    await search_photo_handler(
        message=message,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что функция для работы с БД была вызвана
    mock_search_photo_by_description_in_db.assert_called_once_with(
        pool=mock_pool,
        query=query
    )

    message.answer_photo.assert_called_once()

    state.clear.assert_called_once()

    # Тестируем сценарий с ошибкой
    mock_search_photo_by_description_in_db.side_effect = Exception("Test error")
    message.answer_photo.reset_mock()

    await search_photo_handler(
        message=message,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что вторым вызовом было отправлено сообщение с ошибкой
    message.answer.assert_any_await(LEXICON_RU["error"])


@pytest.mark.asyncio
async def test_search_photo_callback(mock_handler):

    """
    Тестирование хендлера для ответа пользователю на запрос поиска фото.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :return: Функция ничего не возвращает.
    """

    message, callback, state = mock_handler

    callback.data = "search_photo"

    # Запуск хендлера
    await search_photo_callback(
        callback,
        state
    )

    # Проверить, что отправлено сообщение с инструкцией
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU["search_photo"])

    # Проверить, что "часики" убраны
    callback.answer.assert_awaited_once_with()

    # Проверить, что установлено состояние FSM
    state.set_state.assert_awaited_once_with(SearchPhotoState.search_photo)


@pytest.mark.asyncio
async def test_search_photo_callback_error(mock_handler):

    """
    Тестирование хендлера для ответа пользователю по поиску фото с генерацией ошибки.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :return: Функция ничего не возвращает.
    """

    message, callback, state = mock_handler

    callback.data = "search_photo"

    # Исключение для проверки обработки ошибок
    state.set_state = AsyncMock(side_effect=Exception("Test error"))

    # Запуск хендлера
    await search_photo_callback(
        callback,
        state
    )

    # Проверяем, что message.answer вызвался дважды
    assert callback.message.answer.await_count == 2

    # Проверяем, что вторым вызовом было отправлено сообщение с ошибкой
    callback.message.answer.assert_any_await(LEXICON_RU["error"])

    # Проверяем, что был вызван метод answer дважды
    callback.answer.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_category_selection_callback(mock_db_pool,
                                           mock_handler,
                                           keyboards_test_data,
                                           sample_test_data,
                                           mocker):

    """
    Тестирование хендлера выбора категории.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :param keyboards_test_data: Словарь с тестовыми данными клавиатуры.
    :param sample_test_data: Словарь с тестовыми данными.
    :param mocker: Мокер для добавления side_effect в тест для тестирования ошибки.
    :return: Функция ничего не возвращает.
    """

    # Данные для теста
    photo_data = sample_test_data['photo']
    photo_id = photo_data['photo_id']
    category = photo_data['category']
    description = photo_data['description']

    keyboard_pagination = keyboards_test_data['pagination_keyboard']

    # Мокаем функции для работы с БД
    mock_get_photos_from_db = mocker.patch(
        'bot_app.handlers.user_handlers.get_photos_from_db',
        return_value=[photo_data]
    )
    mock_get_total_photos_count = mocker.patch(
        'bot_app.handlers.user_handlers.get_total_photos_count',
        return_value=1
    )

    # Мокаем функцию создания клавиатуры
    mock_create_paginated_keyboard = mocker.patch(
        'bot_app.handlers.user_handlers.create_paginated_keyboard',
        return_value=keyboard_pagination
    )

    # Получаем данные из наших фикстур
    mock_pool, mock_conn = await mock_db_pool(data=photo_data)
    message, callback, state = mock_handler

    # Передаём ожидаемые данные в callback
    callback.data = f'category_{category}'

    # Запуск хендлера
    await category_selection_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что данные категории и страницы успешно обновляются в состоянии
    state.update_data.assert_called_once_with(
        category=category,
        current_page=1
    )

    # Проверяем, что функция для получения фото была вызвана с правильными параметрами
    mock_get_photos_from_db.assert_called_once_with(
        pool=mock_pool,
        category=category,
        limit=5,
        offset=0
    )

    # Проверяем, что функция для получения общего количества фото была вызвана
    mock_get_total_photos_count.assert_called_once_with(
        pool=mock_pool,
        category=category
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_paginated_keyboard.assert_called_once_with(
        current_page=1,
        total_pages=1
    )

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    callback.message.edit_text.assert_awaited_once_with(
        text=f'Выберите сборку из категории {category}:\n'
             f'1. <a href="{photo_id}">{description}</a>\n',
        reply_markup=keyboard_pagination
    )

    # Тестируем сценарий с ошибкой
    mock_get_photos_from_db.side_effect = Exception("Test error")
    message.answer.reset_mock()

    # Запуск хендлера
    await category_selection_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])


@pytest.mark.asyncio
async def test_process_pagination_callback(mock_db_pool,
                                           mock_handler,
                                           keyboards_test_data,
                                           sample_test_data,
                                           mocker):

    """
    Тестирование хендлера обработки пагинации.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :param sample_test_data: Словарь с тестовыми данными.
    :param mocker: Мокер для добавления side_effect в тест для тестирования ошибки.
    :return: Функция ничего не возвращает.
    """

    # Данные для теста
    photo_data = sample_test_data['photo']
    photo_id = photo_data['photo_id']
    description = photo_data['description']

    state_data = sample_test_data['state']
    category = state_data['category']
    current_page = state_data['current_page']

    keyboard_pagination = keyboards_test_data['pagination_keyboard']

    # Мокаем функции для работы с БД
    mock_get_photos_from_db = mocker.patch(
        'bot_app.handlers.user_handlers.get_photos_from_db',
        return_value=[photo_data]
    )
    mock_get_total_photos_count = mocker.patch(
        'bot_app.handlers.user_handlers.get_total_photos_count',
        return_value=1
    )

    # Мокаем функцию создания клавиатуры
    mock_create_paginated_keyboard = mocker.patch(
        'bot_app.handlers.user_handlers.create_paginated_keyboard',
        return_value=keyboard_pagination
    )

    # Получаем данные из наших фикстур
    mock_pool, mock_conn = await mock_db_pool(data=photo_data)
    message, callback, state = mock_handler

    # Передаём ожидаемые данные в callback
    callback.data = f'page_{current_page}'

    state.get_data.return_value = state_data

    # Запуск хендлера
    await process_pagination_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что вызов state.get_data был вызван
    state.get_data.assert_called_once_with()

    # Проверяем, что данные категории и страницы успешно обновляются в состоянии
    state.update_data.assert_called_once_with(current_page=current_page)

    # Проверяем, что функция для получения фото была вызвана с правильными параметрами
    mock_get_photos_from_db.assert_called_once_with(
        pool=mock_pool,
        category=category,
        limit=5,
        offset=5
    )

    # Проверяем, что функция для получения общего количества фото была вызвана
    mock_get_total_photos_count.assert_called_once_with(
        pool=mock_pool,
        category=category
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_paginated_keyboard.assert_called_once_with(
        current_page=current_page,
        total_pages=1
    )

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    callback.message.edit_text.assert_awaited_once_with(
        text=f'Выберите сборку из категории {category}:\n'
             f'1. <a href="{photo_id}">{description}</a>\n',
        reply_markup=keyboard_pagination
    )

    # Тестируем сценарий с ошибкой
    mock_get_photos_from_db.side_effect = Exception("Test error")
    message.answer.reset_mock()

    # Запуск хендлера
    await process_pagination_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])


@pytest.mark.asyncio
async def test_send_photo_handler(mock_db_pool,
                                  mock_handler,
                                  keyboards_test_data,
                                  sample_test_data,
                                  mocker):

    """
    Тестирование хендлера отправки фото пользователю.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :param keyboards_test_data: Словарь с тестовыми данными клавиатуры.
    :param sample_test_data: Словарь с тестовыми данными.
    :param mocker: Мокер для добавления side_effect в тест для тестирования ошибки.
    :return: Функция ничего не возвращает.
    """

    # Данные для теста
    photo_data = sample_test_data['photo']
    photo_id = photo_data['photo_id']
    description = photo_data['description']

    groups_data = sample_test_data['groups']

    user_data = sample_test_data['user']
    user_id = user_data['user_id']

    keyboard_admin = keyboards_test_data['admin_keyboard']

    # Получаем фикстуры
    message, callback, state = mock_handler
    mock_pool, mock_conn = await mock_db_pool(data=groups_data)

    # Настраиваем мок-объекты
    message.text = photo_id
    message.from_user.id = user_id

    # Мокаем функции работы с базой данных
    mock_get_groups_from_db = mocker.patch(
        "bot_app.handlers.user_handlers.get_groups_from_db",
        return_value=groups_data
    )
    mock_get_photo_description_by_file_id_from_db = mocker.patch(
        "bot_app.handlers.user_handlers.get_photo_description_by_file_id_from_db",
        return_value=description
    )

    # Мокаем проверку администратора
    mock_check_is_admin = mocker.patch(
        "bot_app.handlers.user_handlers.check_is_admin",
        return_value=False
    )

    # Мокаем функцию создания клавиатуры
    mock_create_admins_keyboard = mocker.patch(
        'bot_app.handlers.user_handlers.create_admins_keyboard',
        return_value=keyboard_admin
    )

    # Тестируем сценарий для обычного пользователя
    await send_photo_handler(
        message=message,
        dp=mocker.Mock(),
        state=state,
        pool=mock_pool
    )

    # Проверяем вызовы для обычного пользователя
    mock_get_groups_from_db.assert_called_once_with(pool=mock_pool)

    mock_get_photo_description_by_file_id_from_db.assert_called_once_with(
        pool=mock_pool,
        file_id=photo_id
    )

    mock_check_is_admin.assert_called_once_with(
        dp=mocker.ANY,
        user_id=user_id,
        groups_id=groups_data
    )

    message.answer_photo.assert_awaited_once_with(
        photo_id,
        caption=LEXICON_RU['photo_found'] + description
    )

    state.clear.assert_awaited_once()

    # Тестируем сценарий для администратора
    mock_check_is_admin.return_value = True
    message.answer_photo.reset_mock()
    state.clear.reset_mock()

    # Запуск хендлера
    await send_photo_handler(
        message=message,
        dp=mocker.Mock(),
        state=state,
        pool=mock_pool
    )

    # Проверяем вызовы для администратора
    message.answer_photo.assert_awaited_once_with(
        photo_id,
        caption=LEXICON_RU['photo_found'] + description,
        reply_markup=keyboard_admin
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_admins_keyboard.assert_called_once_with()

    state.clear.assert_not_called()

    # Тестируем сценарий с ошибкой
    mock_get_photo_description_by_file_id_from_db.side_effect = Exception("Test error")
    message.answer.reset_mock()

    await send_photo_handler(
        message=message,
        dp=mocker.Mock(),
        state=state,
        pool=mock_pool
    )

    message.answer.assert_awaited_once_with(
        text=LEXICON_RU['error']
    )

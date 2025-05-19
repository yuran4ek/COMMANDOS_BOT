import pytest

from aiogram.utils.keyboard import InlineKeyboardMarkup

from unittest.mock import AsyncMock

from bot_app.exceptions.database import (
    DatabaseGetGroupError,
    DatabaseSearchPhotoByDescriptionError,
    DatabaseGetCategoriesError,
    DatabaseGetPhotosError,
    DatabaseGetTotalPhotosError,
    DatabaseGetFileIdByDescriptionError
)
from bot_app.handlers.user_handlers import (
    search_photo_handler,
    search_photo_callback,
    move_back_to_category_callback,
    category_selection_callback,
    process_pagination_callback,
    send_photo_handler
)
from bot_app.lexicon.lexicon_common.lexicon_ru import LEXICON_RU
from bot_app.states.user_states import SearchPhotoState


@pytest.mark.asyncio
async def test_search_photo_handler(mock_db_pool,
                                    mock_handler,
                                    mock_admin,
                                    sample_test_data,
                                    keyboards_test_data,
                                    mocker):

    """
    Тестирование хендлера для поиска фото.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :param mock_admin: Функция, возвращающая замокированные объекты mock_bot и mock_member.
    :param sample_test_data: Словарь с тестовыми данными.
    :param keyboards_test_data: Словарь с тестовыми данными клавиатуры.
    :param mocker: Мокер для добавления side_effect в тест для тестирования ошибки.
    :return: Функция ничего не возвращает.
    """

    # Данные для теста
    photos_data = sample_test_data['photos']
    photo_data = sample_test_data['photo']
    photo_id = photo_data['photo_id']
    description = photo_data['description']
    category = photo_data['category']
    query = 'Des'
    groups = sample_test_data['groups']

    assemble_buttons = keyboards_test_data['assemble_buttons']
    admins_keyboard = keyboards_test_data['admin_keyboard']

    # Фильтруем данные, которые содержат 'Des' в description
    filtered_data = [
        photo for photo in photos_data if query in photo['description']
    ]

    # Получаем фикстуры
    mock_pool, mock_conn = await mock_db_pool(data=photos_data)
    mock_bot, mock_member = mock_admin
    message, callback, state = mock_handler

    message.text = query

    state.get_data = AsyncMock(return_value={
        'category': category
    })

    # Мокаем функции работы с базой данных
    mock_get_groups_from_db = mocker.patch(
        'bot_app.handlers.user_handlers.get_groups_from_db',
        return_value=groups
    )

    mock_search_photo_by_description_in_db = mocker.patch(
        'bot_app.handlers.user_handlers.search_photo_by_description_in_db',
        return_value=filtered_data
    )

    mock_check_is_admin = mocker.patch(
        'bot_app.handlers.user_handlers.check_is_admin',
        return_value=True
    )

    # Мокаем функцию создания клавиатуры
    mock_create_assembl_buttons = mocker.patch(
        'bot_app.handlers.user_handlers.create_assembl_buttons',
        return_value=assemble_buttons
    )
    mock_create_admins_keyboard = mocker.patch(
        'bot_app.handlers.user_handlers.create_admins_keyboard',
        return_value=admins_keyboard
    )

    # Тестируем сценарий с первым if
    # Запуск хендлера
    await search_photo_handler(
        message=message,
        state=state,
        bot=mock_bot,
        pool=mock_pool
    )

    # Проверяем, что функция для работы с БД была вызвана
    mock_get_groups_from_db.assert_awaited_once_with(pool=mock_pool)

    mock_search_photo_by_description_in_db.assert_awaited_once_with(
        pool=mock_pool,
        category=category,
        query=query
    )

    # Проверяем, что функция проверки на админа была вызвана
    mock_check_is_admin.assert_awaited_once()

    # Проверяем, что сообщение с клавиатурой было успешно отправлено
    message.answer.assert_awaited_once_with(
        text=LEXICON_RU['search_result'],
        reply_markup=assemble_buttons
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_assembl_buttons.assert_called_once()

    # Сбрасываем всё для дальнейшего использования
    message.answer.reset_mock()
    mock_create_assembl_buttons.reset_mock()
    mock_get_groups_from_db.reset_mock()
    mock_check_is_admin.reset_mock()
    mock_search_photo_by_description_in_db.reset_mock()

    # Тестируем сценарий с else
    # Фильтруем данные, которые содержат 'Des' в description
    qry = 'Description'
    message.text = qry
    filtered_data = [
        photo for photo in photos_data if qry in photo['description']
    ]
    mock_search_photo_by_description_in_db.return_value = filtered_data

    # Запуск хендлера
    await search_photo_handler(
        message=message,
        state=state,
        bot=mock_bot,
        pool=mock_pool
    )

    # Проверяем, что функция для работы с БД была вызвана
    mock_search_photo_by_description_in_db.assert_awaited_once_with(
        pool=mock_pool,
        category=category,
        query=qry
    )

    # Проверяем, что функция проверки на админа была вызвана
    mock_check_is_admin.assert_awaited_once()

    # Проверяем, что сообщение с клавиатурой было успешно отправлено
    message.answer_photo.assert_awaited_once_with(
        photo=photo_id,
        caption=f'{LEXICON_RU["photo_found"]} <b>{description}</b>',
        reply_markup=admins_keyboard
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_admins_keyboard.assert_called_once()

    # Проверяем, что обновление в словаре data прошло успешно
    state.update_data.assert_awaited_once_with(
        photo_id=photo_id,
        description=description
    )

    # Сбрасываем всё для дальнейшего использования
    message.answer_photo.reset_mock()
    mock_create_admins_keyboard.reset_mock()
    mock_get_groups_from_db.reset_mock()
    mock_check_is_admin.reset_mock()
    mock_search_photo_by_description_in_db.reset_mock()

    # Тестируем сценарий с else и если не админ
    mock_search_photo_by_description_in_db.return_value = filtered_data
    mock_check_is_admin.return_value = False

    # Запуск хендлера
    await search_photo_handler(
        message=message,
        state=state,
        bot=mock_bot,
        pool=mock_pool
    )

    # Проверяем, что функция для работы с БД была вызвана
    mock_search_photo_by_description_in_db.assert_awaited_once_with(
        pool=mock_pool,
        category=category,
        query=qry
    )

    # Проверяем, что функция проверки на админа была вызвана
    mock_check_is_admin.assert_awaited_once()

    # Проверяем, что сообщение с клавиатурой было успешно отправлено
    message.answer_photo.assert_awaited_once_with(
        photo=photo_id,
        caption=f'{LEXICON_RU["photo_found"]} <b>{description}</b>',
        reply_markup=None
    )

    # Проверяем, что сброса состояния была вызвана
    state.clear.assert_awaited_once()

    # Сбрасываем всё для дальнейшего использования
    message.answer_photo.reset_mock()
    mock_get_groups_from_db.reset_mock()
    mock_check_is_admin.reset_mock()
    mock_search_photo_by_description_in_db.reset_mock()

    # Тестируем сценарий с else
    mock_search_photo_by_description_in_db.return_value = []

    # Запуск хендлера
    await search_photo_handler(
        message=message,
        state=state,
        bot=mock_bot,
        pool=mock_pool
    )

    # Проверяем, что функция для работы с БД была вызвана
    mock_search_photo_by_description_in_db.assert_awaited_once_with(
        pool=mock_pool,
        category=category,
        query=qry
    )

    # Проверяем, что функция проверки на админа была вызвана
    mock_check_is_admin.assert_awaited_once()

    # Проверяем, что сообщение с клавиатурой было успешно отправлено
    message.answer.assert_awaited_once_with(text=LEXICON_RU['photo_not_found'])

    # Сбрасываем всё для дальнейшего использования
    message.answer.reset_mock()
    mock_get_groups_from_db.reset_mock()
    mock_check_is_admin.reset_mock()
    mock_search_photo_by_description_in_db.reset_mock()

    # Тестируем сценарий с ошибкой
    mock_get_groups_from_db.side_effect = DatabaseGetGroupError()

    # Запуск хендлера
    await search_photo_handler(
        message=message,
        state=state,
        bot=mock_bot,
        pool=mock_pool
    )

    # Проверяем, что вторым вызовом было отправлено сообщение с ошибкой
    message.answer.assert_awaited_once_with(text=LEXICON_RU["error"])

    # Сбрасываем всё для дальнейшего использования
    message.answer.reset_mock()
    mock_get_groups_from_db.side_effect = None

    # Тестируем сценарий с ошибкой
    mock_search_photo_by_description_in_db.side_effect = DatabaseSearchPhotoByDescriptionError()

    # Запуск хендлера
    await search_photo_handler(
        message=message,
        state=state,
        bot=mock_bot,
        pool=mock_pool
    )

    # Проверяем, что вторым вызовом было отправлено сообщение с ошибкой
    message.answer.assert_awaited_once_with(text=LEXICON_RU["error"])

    # Сбрасываем всё для дальнейшего использования
    message.answer.reset_mock()
    mock_search_photo_by_description_in_db.side_effect = None

    # Тестируем сценарий с ошибкой
    state.get_data.side_effect = Exception()

    # Запуск хендлера
    await search_photo_handler(
        message=message,
        state=state,
        bot=mock_bot,
        pool=mock_pool
    )

    # Проверяем, что вторым вызовом было отправлено сообщение с ошибкой
    message.answer.assert_awaited_once_with(text=LEXICON_RU["error"])


@pytest.mark.asyncio
async def test_search_photo_callback(mock_db_pool,
                                     mock_handler,
                                     sample_test_data,
                                     mocker):

    """
    Тестирование хендлера для ответа пользователю на запрос поиска фото.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :param sample_test_data: Словарь с тестовыми данными.
    :param mocker: Мокер для добавления side_effect в тест для тестирования ошибки.
    :return: Функция ничего не возвращает.
    """

    # Данные для теста
    category_data = sample_test_data['category']
    photo_data = sample_test_data['photo']
    category = photo_data['category']

    # Получаем фикстуры
    mock_pool, mock_conn = await mock_db_pool(data=category_data)
    message, callback, state = mock_handler

    callback.data = "search_photo"
    state.get_data = AsyncMock(return_value={
        'cancel_handler': False,
        'category': category
    })

    # Мокаем функции работы с базой данных
    mock_get_categories_from_db = mocker.patch(
        'bot_app.handlers.user_handlers.get_categories_from_db',
        return_value=category_data
    )

    # Запуск хендлера
    await search_photo_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что функция для работы с БД была вызвана
    mock_get_categories_from_db.assert_awaited_once_with(pool=mock_pool)

    # Проверить, что отправлено сообщение с инструкцией
    callback.message.edit_text.assert_awaited_once_with(
        text=f'{LEXICON_RU["search_photo"]} <b>{category}</b>',
        reply_markup=None
    )

    # Проверить, что "часики" убраны
    callback.answer.assert_awaited_once()

    # Проверить, что установлено состояние FSM
    state.set_state.assert_awaited_once_with(SearchPhotoState.search_photo)

    # Сбрасываем всё для дальнейшего использования
    callback.answer.reset_mock()
    mock_get_categories_from_db.reset_mock()
    state.get_data.reset_mock()

    # Тестируем else
    state.get_data = AsyncMock(return_value={
        'cancel_handler': True,
        'category': category
    })

    # Запуск хендлера
    await search_photo_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверить, что отправлено сообщение с инструкцией
    callback.answer.assert_awaited_once_with(text=LEXICON_RU['buttons_not_active'])

    # Сбрасываем всё для дальнейшего использования
    callback.answer.reset_mock()
    state.get_data.reset_mock()

    # Тестируем сценарий с ошибкой
    state.get_data = AsyncMock(return_value={
        'cancel_handler': False,
        'category': category
    })
    mock_get_categories_from_db.side_effect = DatabaseGetCategoriesError()

    # Запуск хендлера
    await search_photo_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что было отправлено сообщение с ошибкой
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU["error"])

    # Сбрасываем всё для дальнейшего использования
    callback.message.answer.reset_mock()
    mock_get_categories_from_db.side_effect = None

    # Тестируем сценарий с ошибкой
    state.get_data.side_effect = Exception()

    # Запуск хендлера
    await search_photo_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что было отправлено сообщение с ошибкой
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU["error"])


@pytest.mark.asyncio
async def test_move_back_to_category_callback(mock_db_pool,
                                              mock_handler,
                                              sample_test_data,
                                              keyboards_test_data,
                                              mocker):

    """
    Тестирование хендлера для ответа пользователю на запрос поиска фото.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :param sample_test_data: Словарь с тестовыми данными.
    :param keyboards_test_data: Словарь с тестовыми данными клавиатуры.
    :param mocker: Мокер для добавления side_effect в тест для тестирования ошибки.
    :return: Функция ничего не возвращает.
    """

    # Данные для теста
    category_data = sample_test_data['category']

    categories_keyboard = keyboards_test_data['categories_keyboard']

    # Получаем фикстуры
    mock_pool, mock_conn = await mock_db_pool(data=category_data)
    message, callback, state = mock_handler

    callback.data = "search_photo"
    state.get_data = AsyncMock(return_value={
        'cancel_handler': False
    })

    # Мокаем функции работы с базой данных
    mock_get_categories_from_db = mocker.patch(
        'bot_app.handlers.user_handlers.get_categories_from_db',
        return_value=category_data
    )

    # Мокаем функцию создания клавиатуры
    mock_create_categories_keyboard = mocker.patch(
        'bot_app.handlers.user_handlers.create_categories_keyboard',
        return_value=categories_keyboard
    )

    # Запуск хендлера
    await move_back_to_category_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что функция для работы с БД была вызвана
    mock_get_categories_from_db.assert_awaited_once_with(pool=mock_pool)

    # Проверяем, что сообщение с клавиатурой было успешно отправлено
    callback.message.edit_text.assert_awaited_once_with(
        text=LEXICON_RU['assembl'],
        reply_markup=categories_keyboard
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_categories_keyboard.assert_called_once()

    # Проверяем, что обновление в словаре data прошло успешно
    state.update_data.assert_awaited_once_with(cancel_handler=False)

    # Сбрасываем всё для дальнейшего использования
    callback.message.answer.reset_mock()
    mock_get_categories_from_db.reset_mock()
    state.get_data.reset_mock()

    # Тестируем else
    state.get_data = AsyncMock(return_value={
        'cancel_handler': True
    })

    # Запуск хендлера
    await move_back_to_category_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что сообщение было успешно отправлено
    callback.answer.assert_awaited_once_with(text=LEXICON_RU['buttons_not_active'])

    # Сбрасываем всё для дальнейшего использования
    callback.answer.reset_mock()
    state.get_data.reset_mock()

    # Тестируем сценарий с ошибкой
    state.get_data = AsyncMock(return_value={
        'cancel_handler': False
    })
    mock_get_categories_from_db.side_effect = DatabaseGetCategoriesError()

    # Запуск хендлера
    await move_back_to_category_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что было отправлено сообщение с ошибкой
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU["error"])

    # Сбрасываем всё для дальнейшего использования
    callback.message.answer.reset_mock()
    mock_get_categories_from_db.side_effect = None
    state.get_data.reset_mock()

    # Тестируем сценарий с ошибкой
    state.get_data.side_effect = Exception()

    # Запуск хендлера
    await move_back_to_category_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что было отправлено сообщение с ошибкой
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU["error"])


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
    category = photo_data['category']

    assemble_buttons = keyboards_test_data['assemble_buttons']
    keyboard_pagination = keyboards_test_data['pagination_keyboard']

    full_keyboard = InlineKeyboardMarkup(
        inline_keyboard=assemble_buttons.inline_keyboard + keyboard_pagination.inline_keyboard
    )

    # Получаем данные из наших фикстур
    mock_pool, mock_conn = await mock_db_pool(data=photo_data)
    message, callback, state = mock_handler

    # Передаём ожидаемые данные в callback
    callback.data = f'category_{category}'
    message.text = f'{LEXICON_RU["choose_assembl"]} <b>{category}</b>:\n'

    state.get_data = AsyncMock(return_value={
        'cancel_handler': False
    })

    # Мокаем функции для работы с БД
    mock_get_photos_from_db = mocker.patch(
        'bot_app.handlers.user_handlers.get_photos_from_db',
        return_value=[]
    )
    mock_get_total_photos_count = mocker.patch(
        'bot_app.handlers.user_handlers.get_total_photos_count',
        return_value=1
    )

    # Мокаем функцию создания клавиатуры
    mock_create_assembl_buttons = mocker.patch(
        'bot_app.handlers.user_handlers.create_assembl_buttons',
        return_value=assemble_buttons
    )

    mock_create_paginated_keyboard = mocker.patch(
        'bot_app.handlers.user_handlers.create_paginated_keyboard',
        return_value=keyboard_pagination
    )

    # Тестируем сценарий с if
    # Запуск хендлера
    await category_selection_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что функция для получения фото была вызвана с правильными параметрами
    mock_get_photos_from_db.assert_awaited_once_with(
        pool=mock_pool,
        category=category,
        limit=6,
        offset=0
    )

    # Проверяем, что функция для получения общего количества фото была вызвана
    mock_get_total_photos_count.assert_awaited_once_with(
        pool=mock_pool,
        category=category
    )

    # Проверяем, что данные категории и страницы успешно обновляются в состоянии
    state.update_data.assert_awaited_once_with(
        category=category,
        current_page=1
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_assembl_buttons.assert_called_once()
    mock_create_paginated_keyboard.assert_called_once_with(
        current_page=1,
        total_pages=1
    )

    # Проверяем, что сообщение с текстом было успешно отправлено
    callback.message.edit_text.assert_awaited_once_with(
        text=LEXICON_RU['empty_category']
    )

    # Сбрасываем всё для дальнейшего использования
    callback.message.edit_text.reset_mock()
    mock_get_photos_from_db.reset_mock()
    mock_get_total_photos_count.reset_mock()
    mock_create_paginated_keyboard.reset_mock()
    mock_create_assembl_buttons.reset_mock()
    state.update_data.reset_mock()

    # Тестируем сценарий с else
    # Запуск хендлера
    mock_get_photos_from_db.return_value = [photo_data]

    await category_selection_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что данные категории и страницы успешно обновляются в состоянии
    state.update_data.assert_awaited_once_with(
        category=category,
        current_page=1
    )

    # Проверяем, что функция для получения фото была вызвана с правильными параметрами
    mock_get_photos_from_db.assert_awaited_once_with(
        pool=mock_pool,
        category=category,
        limit=6,
        offset=0
    )

    # Проверяем, что функция для получения общего количества фото была вызвана
    mock_get_total_photos_count.assert_awaited_once_with(
        pool=mock_pool,
        category=category
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_assembl_buttons.assert_called_once()
    mock_create_paginated_keyboard.assert_called_once_with(
        current_page=1,
        total_pages=1
    )

    # Проверяем, что сообщение удалено
    callback.message.delete.assert_awaited_once()

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    callback.message.answer.assert_awaited_once_with(
        text=message.text,
        reply_markup=full_keyboard
        )

    # Сбрасываем всё для дальнейшего использования
    callback.message.answer.reset_mock()
    callback.message.photo = False
    mock_get_photos_from_db.reset_mock()
    mock_get_total_photos_count.reset_mock()
    mock_create_paginated_keyboard.reset_mock()
    mock_create_assembl_buttons.reset_mock()
    state.update_data.reset_mock()

    # Запуск хендлера
    mock_get_photos_from_db.return_value = [photo_data]

    await category_selection_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что данные категории и страницы успешно обновляются в состоянии
    state.update_data.assert_awaited_once_with(
        category=category,
        current_page=1
    )

    # Проверяем, что функция для получения фото была вызвана с правильными параметрами
    mock_get_photos_from_db.assert_awaited_once_with(
        pool=mock_pool,
        category=category,
        limit=6,
        offset=0
    )

    # Проверяем, что функция для получения общего количества фото была вызвана
    mock_get_total_photos_count.assert_awaited_once_with(
        pool=mock_pool,
        category=category
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_assembl_buttons.assert_called_once()
    mock_create_paginated_keyboard.assert_called_once_with(
        current_page=1,
        total_pages=1
    )

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    callback.message.edit_text.assert_awaited_once_with(
        text=message.text,
        reply_markup=full_keyboard
    )

    # Сбрасываем всё для дальнейшего использования
    callback.message.edit_text.reset_mock()
    mock_get_photos_from_db.reset_mock()
    mock_get_total_photos_count.reset_mock()
    mock_create_paginated_keyboard.reset_mock()
    mock_create_assembl_buttons.reset_mock()
    state.update_data.reset_mock()

    # Тестируем else
    state.get_data = AsyncMock(return_value={
        'cancel_handler': True
    })

    # Запуск хендлера
    mock_get_photos_from_db.return_value = [photo_data]

    await category_selection_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что отправлено сообщение с необходимым текстом
    callback.answer.assert_awaited_once_with(text=LEXICON_RU['buttons_not_active'])

    # Сбрасываем всё для дальнейшего использования
    callback.answer.reset_mock()
    state.get_data.reset_mock()

    # Тестируем сценарий с ошибкой
    state.get_data = AsyncMock(return_value={
        'cancel_handler': False
    })

    mock_get_photos_from_db.side_effect = DatabaseGetPhotosError()

    # Запуск хендлера
    await category_selection_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Сбрасываем всё для дальнейшего использования
    callback.message.answer.reset_mock()
    mock_get_photos_from_db.side_effect = None

    # Тестируем сценарий с ошибкой
    mock_get_total_photos_count.side_effect = DatabaseGetTotalPhotosError()

    # Запуск хендлера
    await category_selection_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Сбрасываем всё для дальнейшего использования
    callback.message.answer.reset_mock()
    mock_get_total_photos_count.side_effect = None

    # Тестируем сценарий с ошибкой
    state.get_data.side_effect = Exception()

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

    state_data = sample_test_data['state']
    category = state_data['category']
    current_page = state_data['current_page']

    keyboard_pagination = keyboards_test_data['pagination_keyboard']
    assemble_buttons = keyboards_test_data['assemble_buttons']

    full_keyboard = InlineKeyboardMarkup(
        inline_keyboard=assemble_buttons.inline_keyboard + keyboard_pagination.inline_keyboard
    )

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
    mock_create_assembl_buttons = mocker.patch(
        'bot_app.handlers.user_handlers.create_assembl_buttons',
        return_value=assemble_buttons
    )

    # Получаем данные из наших фикстур
    mock_pool, mock_conn = await mock_db_pool(data=photo_data)
    message, callback, state = mock_handler

    # Передаём ожидаемые данные в callback
    callback.data = f'page_{current_page}'

    state.get_data = AsyncMock(return_value={
        'cancel_handler': False,
        'category': category
    })

    # Запуск хендлера
    await process_pagination_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что вызов state.get_data был вызван
    state.get_data.assert_awaited_once()

    # Проверяем, что данные категории и страницы успешно обновляются в состоянии
    state.update_data.assert_awaited_once_with(current_page=current_page)

    # Проверяем, что функция для получения фото была вызвана с правильными параметрами
    mock_get_photos_from_db.assert_awaited_once_with(
        pool=mock_pool,
        category=category,
        limit=6,
        offset=6
    )

    # Проверяем, что функция для получения общего количества фото была вызвана
    mock_get_total_photos_count.assert_awaited_once_with(
        pool=mock_pool,
        category=category
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_assembl_buttons.assert_called_once()
    mock_create_paginated_keyboard.assert_called_once_with(
        current_page=current_page,
        total_pages=1
    )

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    callback.message.edit_text.assert_awaited_once_with(
        text=f'{LEXICON_RU["choose_assembl"]} <b>{category}</b>:\n',
        reply_markup=full_keyboard
    )

    # Сбрасываем всё для дальнейшего использования
    mock_get_photos_from_db.reset_mock()
    mock_get_total_photos_count.reset_mock()
    mock_create_paginated_keyboard.reset_mock()
    mock_create_assembl_buttons.reset_mock()
    state.get_data.reset_mock()

    # Тестируем else
    state.get_data = AsyncMock(return_value={
        'cancel_handler': True
    })

    # Запуск хендлера
    mock_get_photos_from_db.return_value = [photo_data]

    await category_selection_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что отправлено сообщение с необходимым текстом
    callback.answer.assert_awaited_once_with(text=LEXICON_RU['buttons_not_active'])

    # Сбрасываем всё для дальнейшего использования
    callback.answer.reset_mock()
    state.get_data.reset_mock()

    # Тестируем сценарий с ошибкой
    state.get_data = AsyncMock(return_value={
        'cancel_handler': False
    })

    mock_get_photos_from_db.side_effect = DatabaseGetPhotosError()

    # Запуск хендлера
    await process_pagination_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Сбрасываем всё для дальнейшего использования
    callback.message.answer.reset_mock()
    mock_get_photos_from_db.side_effect = None

    # Тестируем сценарий с ошибкой
    mock_get_total_photos_count.side_effect = DatabaseGetTotalPhotosError()

    # Запуск хендлера
    await process_pagination_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Сбрасываем всё для дальнейшего использования
    callback.message.answer.reset_mock()
    mock_get_total_photos_count.side_effect = None

    # Тестируем сценарий с ошибкой
    state.get_data.side_effect = Exception()

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
    photo_id = ''
    category = photo_data['category']

    groups_data = sample_test_data['groups']

    keyboard_admin = keyboards_test_data['admin_keyboard']

    # Получаем фикстуры
    message, callback, state = mock_handler
    mock_pool, mock_conn = await mock_db_pool(data=photo_data)

    # Настраиваем мок-объекты
    caption = photo_data['description']
    callback.data = f'photo_{caption}'

    state.get_data = AsyncMock(return_value={
        'cancel_handler': False,
        'category': category
    })

    # Мокаем функции работы с базой данных
    mock_get_groups_from_db = mocker.patch(
        "bot_app.handlers.user_handlers.get_groups_from_db",
        return_value=groups_data
    )
    mock_get_photo_file_id_by_description_from_db = mocker.patch(
        "bot_app.handlers.user_handlers.get_photo_file_id_by_description_from_db",
        return_value=photo_id
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

    # Тестируем сценарий с if
    # Запуск хендлера
    await send_photo_handler(
        callback=callback,
        bot=mocker.Mock(),
        state=state,
        pool=mock_pool
    )

    # Проверяем вызовы
    mock_get_groups_from_db.assert_awaited_once_with(pool=mock_pool)
    mock_get_photo_file_id_by_description_from_db.assert_awaited_once_with(
        pool=mock_pool,
        description=caption
    )

    # Проверяем, что сообщение с текстом было успешно отправлено
    callback.message.edit_text.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Сбрасываем всё для дальнейшего тестирования
    mock_get_groups_from_db.reset_mock()
    mock_get_photo_file_id_by_description_from_db.reset_mock()
    callback.answer.reset_mock()
    callback.message.edit_text.reset_mock()

    # Тестируем else
    photo_id = photo_data['photo_id']
    description = f'{LEXICON_RU["photo_found"]} <b>{caption}</b>'
    mock_get_photo_file_id_by_description_from_db.return_value = photo_id

    # Запуск хендлера
    await send_photo_handler(
        callback=callback,
        bot=mocker.Mock(),
        state=state,
        pool=mock_pool
    )

    # Проверяем вызовы
    mock_get_groups_from_db.assert_awaited_once_with(pool=mock_pool)
    mock_get_photo_file_id_by_description_from_db.assert_awaited_once_with(
        pool=mock_pool,
        description=caption
    )
    mock_check_is_admin.assert_awaited_once()

    # Проверяем, что сообщение с текстом было успешно отправлено
    callback.message.answer_photo.assert_awaited_once_with(
        photo=photo_id,
        caption=description
    )

    state.clear.assert_awaited_once()

    # Сбрасываем всё для дальнейшего тестирования
    mock_get_groups_from_db.reset_mock()
    mock_get_photo_file_id_by_description_from_db.reset_mock()
    mock_check_is_admin.reset_mock()
    callback.message.answer_photo.reset_mock()
    callback.answer.reset_mock()
    state.clear.reset_mock()

    # Тестируем сценарий для администратора
    mock_check_is_admin.return_value = True

    # Запуск хендлера
    await send_photo_handler(
        callback=callback,
        bot=mocker.Mock(),
        state=state,
        pool=mock_pool
    )

    # Проверяем вызовы
    mock_get_groups_from_db.assert_awaited_once_with(pool=mock_pool)
    mock_get_photo_file_id_by_description_from_db.assert_awaited_once_with(
        pool=mock_pool,
        description=caption
    )
    mock_check_is_admin.assert_awaited_once()

    # Проверяем, что сообщение было удалено
    callback.message.delete.assert_awaited_once()

    # Проверяем, что данные успешно обновляются в состоянии
    state.update_data.assert_awaited_once_with(
        photo_id=photo_id,
        description=caption
    )

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    callback.message.answer_photo.assert_awaited_once_with(
        photo=photo_id,
        caption=description,
        reply_markup=keyboard_admin
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_admins_keyboard.assert_called_once()

    # Сбрасываем всё для дальнейшего тестирования
    mock_get_groups_from_db.reset_mock()
    mock_get_photo_file_id_by_description_from_db.reset_mock()
    mock_check_is_admin.reset_mock()
    callback.answer.reset_mock()
    state.get_data.reset_mock()

    # Тестируем else
    state.get_data = AsyncMock(return_value={
        'cancel_handler': True
    })

    # Запуск хендлера
    await send_photo_handler(
        callback=callback,
        bot=mocker.Mock(),
        state=state,
        pool=mock_pool
    )

    # Проверяем, что отправлено сообщение с необходимым текстом
    callback.answer.assert_awaited_once_with(text=LEXICON_RU['buttons_not_active'])

    # Сбрасываем всё для дальнейшего использования
    callback.answer.reset_mock()
    state.get_data.reset_mock()

    # Тестируем сценарий с ошибкой
    state.get_data = AsyncMock(return_value={
        'cancel_handler': False,
        'category': category
    })

    mock_get_groups_from_db.side_effect = DatabaseGetGroupError()

    # Запуск хендлера
    await send_photo_handler(
        callback=callback,
        bot=mocker.Mock(),
        state=state,
        pool=mock_pool
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Сбрасываем всё для дальнейшего использования
    callback.message.answer.reset_mock()
    mock_get_groups_from_db.side_effect = None

    # Тестируем сценарий с ошибкой
    mock_get_photo_file_id_by_description_from_db.side_effect = DatabaseGetFileIdByDescriptionError()

    # Запуск хендлера
    await send_photo_handler(
        callback=callback,
        bot=mocker.Mock(),
        state=state,
        pool=mock_pool
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Сбрасываем всё для дальнейшего использования
    callback.message.answer.reset_mock()
    mock_get_photo_file_id_by_description_from_db.side_effect = None

    # Тестируем сценарий с ошибкой
    state.get_data.side_effect = Exception()

    # Запуск хендлера
    await send_photo_handler(
        callback=callback,
        bot=mocker.Mock(),
        state=state,
        pool=mock_pool
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

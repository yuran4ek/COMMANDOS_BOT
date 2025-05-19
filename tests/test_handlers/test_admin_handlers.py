import pytest

from unittest.mock import (
    AsyncMock,
    Mock,
    call
)

from bot_app.exceptions.database import (
    DatabaseGetGroupError,
    DatabaseGetCategoriesError,
    DatabaseAddPhotoWithCategoryError,
    DatabaseDeletePhotoError,
    DatabaseUpdatePhotoDescriptionError,
    DatabaseUpdatePhotoError,
    DatabaseGetPhotoDescriptionByFileIdError,
)
from bot_app.exceptions.photo import PhotoAlreadyExistsError
from bot_app.handlers.admin_handlers import (
    update_photo_handler,
    check_message_for_photo,
    process_delete_photo_callback,
    process_update_photo_callback,
    process_update_photo_description,
    update_photo_description_handler,
    process_confirm_callback,

)
from bot_app.lexicon.lexicon_common.lexicon_ru import LEXICON_RU
from bot_app.states.admin_states import AdminUpdateDescriptionState


@pytest.mark.asyncio
async def test_update_photo_handler(mock_db_pool,
                                    mock_handler,
                                    mock_admin,
                                    keyboards_test_data,
                                    sample_test_data,
                                    mocker):

    """
    Тестирование хендлера изменения фото в БД администратором.
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
    new_photo_id = photo_data['new_photo_id']
    description = photo_data['description']
    category = photo_data['category']

    groups_data = sample_test_data['groups']

    user_data = sample_test_data['user']
    user_id = user_data['user_id']

    keyboard_confirmation = keyboards_test_data['confirmation_keyboard']

    # Получаем фикстуры
    message, callback, state = mock_handler
    mock_pool, mock_conn = await mock_db_pool(data=groups_data)
    mock_bot, mock_member = mock_admin

    state.get_data = AsyncMock(return_value={
        'cancel_handler': False,
        'photo_id': photo_id,
        'category': category
    })

    # Настраиваем мок-объекты
    message.from_user.id = user_id
    message.photo[-1].file_id = new_photo_id

    # Мокаем функции работы с базой данных
    mock_get_groups_from_db = mocker.patch(
        "bot_app.handlers.admin_handlers.get_groups_from_db",
        return_value=groups_data
    )

    mock_get_photo_description_by_file_id_from_db = mocker.patch(
        'bot_app.handlers.admin_handlers.get_photo_description_by_file_id_from_db',
        return_value=description
    )

    mock_check_is_admin = mocker.patch(
        'bot_app.handlers.admin_handlers.check_is_admin',
        return_value=True
    )

    # Мокаем функцию создания клавиатуры
    mock_create_admins_confirmation_keyboard = mocker.patch(
        'bot_app.handlers.admin_handlers.create_admins_confirmation_keyboard',
        return_value=keyboard_confirmation
    )

    # Запуск хендлера
    await update_photo_handler(
        message=message,
        bot=mock_bot,
        pool=mock_pool,
        state=state
    )

    # Проверяем вызовы
    mock_get_groups_from_db.assert_awaited_once_with(pool=mock_pool)
    mock_get_photo_description_by_file_id_from_db.assert_awaited_once_with(
        pool=mock_pool,
        file_id=photo_id
    )
    mock_check_is_admin.assert_awaited_once()

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    message.answer_photo.assert_awaited_once_with(
        photo=new_photo_id,
        caption=f'{LEXICON_RU["update_photo_in_db"]} <b>{description}</b> '
                f'{LEXICON_RU["add_photo_category_to_db"]} <b>{category}</b>\n'
                f'{LEXICON_RU["confirm"]}',
        reply_markup=keyboard_confirmation
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_admins_confirmation_keyboard.assert_called_once()

    # проверяем, что данные в словаре data у state обновлены с правильными параметрами
    state.update_data.assert_awaited_once_with(new_photo_id=new_photo_id)

    # Сбрасываем отправку сообщений для дальнейшего тестирования
    message.answer.reset_mock()
    mock_get_groups_from_db.reset_mock()
    mock_check_is_admin.reset_mock()

    # Если пользователь не админ
    mock_check_is_admin.return_value = False

    # Запуск хендлера
    await update_photo_handler(
        message=message,
        bot=mock_bot,
        pool=mock_pool,
        state=state
    )

    # Проверяем вызовы
    mock_get_groups_from_db.assert_awaited_once_with(pool=mock_pool)
    mock_check_is_admin.assert_awaited_once()

    # Проверяем, что сообщение с текстом было успешно отправлено
    message.answer.assert_awaited_once_with(text=LEXICON_RU['user_not_admin'])

    # Сбрасываем отправку сообщений для дальнейшего тестирования
    message.answer.reset_mock()

    # Тестируем сценарий с ошибкой
    mock_get_groups_from_db.side_effect = DatabaseGetGroupError()
    # Если пользователь не админ
    mock_check_is_admin.return_value = True

    # Запуск хендлера
    await update_photo_handler(
        message=message,
        bot=mock_bot,
        pool=mock_pool,
        state=state
    )
    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    message.answer.assert_awaited_once_with(text=LEXICON_RU["error"])

    # Сбрасываем отправку сообщений для дальнейшего тестирования
    message.answer.reset_mock()
    # Сбрасываем side_effect
    mock_get_groups_from_db.side_effect = None

    # Тестируем сценарий с ошибкой
    mock_get_photo_description_by_file_id_from_db.side_effect = DatabaseGetPhotoDescriptionByFileIdError()
    # Запуск хендлера
    await update_photo_handler(
        message=message,
        bot=mock_bot,
        pool=mock_pool,
        state=state
    )
    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    message.answer.assert_awaited_once_with(text=LEXICON_RU["error"])

    # Сбрасываем отправку сообщений для дальнейшего тестирования
    message.answer.reset_mock()
    # Сбрасываем side_effect
    mock_get_photo_description_by_file_id_from_db.side_effect = None


@pytest.mark.asyncio
async def test_check_message_for_photo(mock_db_pool,
                                       mock_handler,
                                       mock_admin,
                                       keyboards_test_data,
                                       sample_test_data,
                                       mocker):

    """
    Тестирование хендлера добавления фото в БД администратором.
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
    category = photo_data['category']

    categories_data = sample_test_data['category']
    groups_data = sample_test_data['groups']

    user_data = sample_test_data['user']
    user_id = user_data['user_id']

    transliterate_filter = sample_test_data['transliterate_filter']

    keyboard_confirmation = keyboards_test_data['confirmation_keyboard']

    # Получаем фикстуры
    message, callback, state = mock_handler
    mock_pool, mock_conn = await mock_db_pool(data=categories_data)
    mock_bot, mock_member = mock_admin

    # Настраиваем мок-объекты
    message.caption = f'{category} {description}'
    message.from_user.id = user_id
    message.photo[-1].file_id = photo_id

    # Мокаем функции работы с базой данных
    mock_get_categories_from_db = mocker.patch(
        "bot_app.handlers.admin_handlers.get_categories_from_db",
        return_value=categories_data
    )
    mock_get_groups_from_db = mocker.patch(
        "bot_app.handlers.admin_handlers.get_groups_from_db",
        return_value=groups_data
    )

    mock_check_is_admin = mocker.patch(
        'bot_app.handlers.admin_handlers.check_is_admin',
        return_value=True
    )

    # Мокаем функцию создания клавиатуры
    mock_create_admins_confirmation_keyboard = mocker.patch(
        'bot_app.handlers.admin_handlers.create_admins_confirmation_keyboard',
        return_value=keyboard_confirmation
    )

    message.chat.type = 'private'

    # Мокаем фильтр
    mock_translit_filter = AsyncMock(return_value=transliterate_filter)

    mock_translit_filter_class = mocker.patch(
        'bot_app.handlers.admin_handlers.TransliterationFilter',
        return_value=mock_translit_filter
    )

    # Запуск хендлера
    await check_message_for_photo(
        message=message,
        bot=mock_bot,
        pool=mock_pool,
        state=state
    )

    # Проверяем вызовы
    mock_get_categories_from_db.assert_awaited_once_with(pool=mock_pool)
    mock_get_groups_from_db.assert_awaited_once_with(pool=mock_pool)
    mock_translit_filter_class.assert_called_once_with(mode='add')
    mock_check_is_admin.assert_awaited_once()

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    message.answer.assert_awaited_once_with(
        text=f'{LEXICON_RU["add_photo_to_db"]} <b>{description}</b> '
             f'{LEXICON_RU["add_photo_category_to_db"]} <b>{category}</b>\n'
             f'{LEXICON_RU["confirm"]}',
        reply_markup=keyboard_confirmation
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_admins_confirmation_keyboard.assert_called_once()

    # проверяем, что данные в словаре data у state обновлены с правильными параметрами
    assert state.update_data.call_args_list == [
        call(cancel_handler=False),
        call(
            photo_id=photo_id,
            category=category,
            description=transliterate_filter['description'],
            description_translit=transliterate_filter['description_translit']
        )
    ]

    # Сбрасываем отправку сообщений для дальнейшего тестирования
    message.answer.reset_mock()
    mock_get_categories_from_db.reset_mock()
    mock_get_groups_from_db.reset_mock()
    mock_check_is_admin.reset_mock()
    mock_translit_filter_class.reset_mock()
    state.update_data.reset_mock()

    # Если пользователь не админ
    mock_check_is_admin.return_value = False

    # Настраиваем мок-объекты
    message.caption = f'{category} {description}'

    # Запуск хендлера
    await check_message_for_photo(
        message=message,
        bot=mock_bot,
        pool=mock_pool,
        state=state
    )

    # Проверяем вызовы
    mock_get_categories_from_db.assert_awaited_once_with(pool=mock_pool)
    mock_get_groups_from_db.assert_awaited_once_with(pool=mock_pool)
    mock_translit_filter_class.assert_called_once_with(mode='add')
    mock_check_is_admin.assert_awaited_once()

    # проверяем, что данные в словаре data у state обновлены с правильными параметрами
    state.update_data.assert_awaited_once_with(cancel_handler=False)

    # Проверяем, что сообщение с текстом было успешно отправлено
    message.answer.assert_awaited_once_with(text=LEXICON_RU['user_not_admin'])

    # Сбрасываем отправку сообщений для дальнейшего тестирования
    message.answer.reset_mock()
    mock_get_categories_from_db.reset_mock()
    mock_get_groups_from_db.reset_mock()
    mock_check_is_admin.reset_mock()
    mock_translit_filter_class.reset_mock()
    mock_create_admins_confirmation_keyboard.reset_mock()
    state.update_data.reset_mock()

    # Если пользователь админ
    mock_check_is_admin.return_value = True

    # Задаём несуществующую категорию
    category_not_found = 'Cat321'
    # Настраиваем мок-объекты
    message.caption = f'{category_not_found} {description}'

    # Запуск хендлера
    await check_message_for_photo(
        message=message,
        bot=mock_bot,
        pool=mock_pool,
        state=state
    )

    # Проверяем вызовы
    mock_get_categories_from_db.assert_awaited_once_with(pool=mock_pool)
    mock_get_groups_from_db.assert_awaited_once_with(pool=mock_pool)
    mock_translit_filter_class.assert_called_once_with(mode='add')
    mock_check_is_admin.assert_awaited_once()

    # Проверяем, что сообщение с текстом было успешно отправлено
    message.answer.assert_awaited_once_with(
        text=f'{LEXICON_RU["category"]} <b>{category_not_found}</b> {LEXICON_RU["category_not_found"]}\n'
             f'{LEXICON_RU["confirm"]}',
        reply_markup=keyboard_confirmation
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_admins_confirmation_keyboard.assert_called_once()

    # проверяем, что данные в словаре data у state обновлены с правильными параметрами
    assert state.update_data.call_args_list == [
        call(cancel_handler=False),
        call(
            photo_id=photo_id,
            category=category_not_found,
            description=transliterate_filter['description'],
            description_translit=transliterate_filter['description_translit']
        )
    ]

    # Сбрасываем отправку сообщений для дальнейшего тестирования
    message.answer.reset_mock()
    mock_get_categories_from_db.reset_mock()
    state.update_data.reset_mock()

    # Тестируем сценарий с ошибкой
    mock_get_categories_from_db.side_effect = DatabaseGetCategoriesError()

    # Запуск хендлера
    await check_message_for_photo(
        message=message,
        bot=mock_bot,
        pool=mock_pool,
        state=state
    )
    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Сбрасываем отправку сообщений для дальнейшего тестирования
    message.answer.reset_mock()
    # Сбрасываем side_effect
    mock_get_categories_from_db.side_effect = None

    # Тестируем сценарий с ошибкой
    mock_get_groups_from_db.side_effect = DatabaseGetGroupError()

    # Запуск хендлера
    await check_message_for_photo(
        message=message,
        bot=mock_bot,
        pool=mock_pool,
        state=state
    )
    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Сбрасываем отправку сообщений для дальнейшего тестирования
    message.answer.reset_mock()
    # Сбрасываем side_effect
    mock_get_groups_from_db.side_effect = None

    message.chat.type = None

    # Запуск хендлера
    await check_message_for_photo(
        message=message,
        bot=mock_bot,
        pool=mock_pool,
        state=state
    )


@pytest.mark.asyncio
async def test_process_delete_photo_callback(mock_handler,
                                             keyboards_test_data,
                                             mocker):

    """
    Тестирование хендлера обработки нажатия кнопки "Удалить" администратором.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :param keyboards_test_data: Словарь с тестовыми данными клавиатуры.
    :param mocker: Мокер для добавления side_effect в тест для тестирования ошибки.
    :return: Функция ничего не возвращает.
    """

    # Данные для теста
    keyboard_confirmation = keyboards_test_data['confirmation_keyboard']

    # Получаем фикстуры
    message, callback, state = mock_handler

    state.get_data = AsyncMock(return_value={
        'cancel_handler': False
    })

    # Мокаем функцию создания клавиатуры
    mock_create_admins_confirmation_keyboard = mocker.patch(
        'bot_app.handlers.admin_handlers.create_admins_confirmation_keyboard',
        return_value=keyboard_confirmation
    )

    callback.message.caption = True

    # Запуск хендлера
    await process_delete_photo_callback(
        callback=callback,
        state=state
    )

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    callback.message.edit_caption.assert_awaited_once_with(
        caption=LEXICON_RU['delete_photo'],
        reply_markup=keyboard_confirmation
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_admins_confirmation_keyboard.assert_called_once()
    callback.answer.assert_awaited_once()

    # Тестируем сценарий с ошибкой
    callback.message.caption = False
    callback.message.edit_caption.reset_mock()

    # Запуск хендлера
    await process_delete_photo_callback(
        callback=callback,
        state=state
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Тестируем сценарий с отменой операции пользователем
    state.get_data.reset_mock()
    callback.answer.reset_mock()

    # Мокаем данные в словаре data
    state.get_data = AsyncMock(return_value={
        'cancel_handler': True
    })

    # Запуск хендлера
    await process_delete_photo_callback(
        callback=callback,
        state=state
    )

    # Проверяем, что в случае отмены будет отправлено сообщение с необходимым текстом
    callback.answer.assert_awaited_once_with(text=LEXICON_RU['buttons_not_active'])


@pytest.mark.asyncio
async def test_process_update_photo_callback(mock_handler,
                                             keyboards_test_data):

    """
    Тестирование хендлера обработки нажатия кнопки "Заменить" администратором.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :param keyboards_test_data: Словарь с тестовыми данными клавиатуры.
    :return: Функция ничего не возвращает.
    """

    # Получаем фикстуры
    message, callback, state = mock_handler

    state.get_data = AsyncMock(return_value={
        'cancel_handler': False
    })

    callback.message.caption = True

    # Запуск хендлера
    await process_update_photo_callback(
        callback=callback,
        state=state
    )

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    callback.message.edit_caption.assert_awaited_once_with(
        caption=LEXICON_RU['update_photo'],
        reply_markup=None
    )

    # проверяем, что данные в словаре data у state обновлены с правильными параметрами
    state.set_state.assert_awaited_once_with(AdminUpdateDescriptionState.update_photo)

    # Тестируем сценарий с ошибкой
    callback.message.caption = False
    callback.message.edit_caption.reset_mock()

    # Запуск хендлера
    await process_update_photo_callback(
        callback=callback,
        state=state
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Тестируем сценарий с отменой операции пользователем
    state.get_data.reset_mock()

    # Мокаем данные в словаре data
    state.get_data = AsyncMock(return_value={
        'cancel_handler': True
    })

    # Запуск хендлера
    await process_update_photo_callback(
        callback=callback,
        state=state
    )

    # Проверяем, что в случае отмены будет отправлено сообщение с необходимым текстом
    callback.answer.assert_awaited_once_with(text=LEXICON_RU['buttons_not_active'])


@pytest.mark.asyncio
async def test_process_update_photo_description(mock_db_pool,
                                                mock_handler,
                                                keyboards_test_data,
                                                sample_test_data,
                                                mocker):

    """
    Тестирование хендлера редактирования описания фото в БД администратором.
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

    # Получаем фикстуры
    message, callback, state = mock_handler
    mock_pool, mock_conn = await mock_db_pool(data=photo_id)

    state.get_data = AsyncMock(return_value={
        'cancel_handler': False,
        'photo_id': photo_id
    })

    callback.message.photo = [Mock(file_id=photo_id)]

    callback.message.caption = True

    # Мокаем функции работы с базой данных
    mock_get_photo_description_by_file_id_from_db = mocker.patch(
        "bot_app.handlers.admin_handlers.get_photo_description_by_file_id_from_db",
        return_value=description
    )

    # Запуск хендлера
    await process_update_photo_description(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем вызовы
    mock_get_photo_description_by_file_id_from_db.assert_awaited_once_with(
        pool=mock_pool,
        file_id=photo_id
    )

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    callback.message.edit_caption.assert_awaited_once_with(
        caption=f'{LEXICON_RU["update_photo_description"]}'
                f'{description}',
        reply_markup=None
    )

    # Проверяем, что установлено состояние FSM
    state.set_state.assert_awaited_once_with(AdminUpdateDescriptionState.update_description)

    # Проверяем, что данные фото успешно обновляются в состоянии
    state.update_data.assert_awaited_once_with(photo_id=photo_id)

    # Тестируем сценарий с ошибкой
    callback.message.edit_caption.reset_mock()
    callback.message.caption = False

    # Запуск хендлера
    await process_update_photo_description(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Тестируем сценарий с ошибкой
    callback.message.edit_caption.reset_mock()
    callback.message.answer.reset_mock()
    mock_get_photo_description_by_file_id_from_db.reset_mock()

    callback.message.caption = True

    mock_get_photo_description_by_file_id_from_db.side_effect = DatabaseGetPhotoDescriptionByFileIdError()

    # Запуск хендлера
    await process_update_photo_description(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Тестируем сценарий с ошибкой
    callback.message.edit_caption.reset_mock()
    callback.message.answer.reset_mock()
    mock_get_photo_description_by_file_id_from_db.side_effect = None

    callback.message.caption = True

    mock_get_photo_description_by_file_id_from_db.side_effect = Exception()

    # Запуск хендлера
    await process_update_photo_description(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Тестируем сценарий с отменой операции пользователем
    state.get_data.reset_mock()

    # Мокаем данные в словаре data
    state.get_data = AsyncMock(return_value={
        'cancel_handler': True
    })

    # Запуск хендлера
    await process_update_photo_description(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что в случае отмены будет отправлено сообщение с необходимым текстом
    callback.answer.assert_awaited_once_with(text=LEXICON_RU['buttons_not_active'])


@pytest.mark.asyncio
async def test_update_photo_description_handler(mock_handler,
                                                keyboards_test_data,
                                                sample_test_data,
                                                mocker
                                                ):

    """
    Тестирование хендлера редактирования описания фото пользователем.
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

    transliterate_filter = sample_test_data['transliterate_filter']

    keyboard_confirmation = keyboards_test_data['confirmation_keyboard']

    # Получаем фикстуры
    message, callback, state = mock_handler

    state.get_data = AsyncMock(return_value={
        'photo_id': photo_id
    })

    message.text = description

    # Мокаем функцию создания клавиатуры
    mock_create_admins_confirmation_keyboard = mocker.patch(
        'bot_app.handlers.admin_handlers.create_admins_confirmation_keyboard',
        return_value=keyboard_confirmation
    )

    # Мокаем фильтр
    mock_translit_filter = AsyncMock(return_value=transliterate_filter)

    mock_translit_filter_class = mocker.patch(
        'bot_app.handlers.admin_handlers.TransliterationFilter',
        return_value=mock_translit_filter
    )

    # Запуск хендлера
    await update_photo_description_handler(
        message=message,
        state=state
    )

    # Проверяем вызовы
    mock_translit_filter_class.assert_called_once_with(mode='update')

    # Проверяем, что данные фото успешно обновляются в состоянии
    state.update_data.assert_awaited_once_with(
        new_description=transliterate_filter['description'],
        new_description_translit=transliterate_filter['description_translit']
    )

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    message.answer_photo.assert_awaited_once_with(
        photo=photo_id,
        caption=f'{LEXICON_RU["new_photo_description"]}\n'
                f'<b>{message.text}</b>\n'
                f'{LEXICON_RU["confirm"]}',
        reply_markup=keyboard_confirmation
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_admins_confirmation_keyboard.assert_called_once()

    # Тестируем сценарий с ошибкой
    message.answer_photo.reset_mock()
    state.get_data.reset_mock()
    state.get_data = AsyncMock(return_value=None)

    # Запуск хендлера
    await update_photo_description_handler(
        message=message,
        state=state
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Тестируем сценарий с ошибкой
    message.answer_photo.reset_mock()
    message.answer.reset_mock()
    state.get_data.reset_mock()
    state.get_data = Exception()

    # Запуск хендлера
    await update_photo_description_handler(
        message=message,
        state=state
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])


@pytest.mark.asyncio
async def test_process_confirm_callback(mock_db_pool,
                                        mock_handler,
                                        keyboards_test_data,
                                        sample_test_data,
                                        mocker
                                        ):

    """
    Тестирование хендлера обработки нажатия кнопок "Да" или "Нет" пользователем.
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

    text_data = sample_test_data['text']
    transliterated_text = text_data['transliterated_text']

    state_data = sample_test_data['state']
    new_photo_id = state_data['new_photo_id']
    new_description = state_data['new_description']
    new_description_translit = state_data['new_description_translit']

    command_data = sample_test_data['command']

    # Получаем фикстуры
    message, callback, state = mock_handler
    mock_pool, mock_conn = await mock_db_pool(data=photo_data)

    state.get_data = AsyncMock(return_value={
        'cancel_handler': False
    })

    # Мокаем функции для работы с БД
    mock_get_photo_description_by_file_id_from_db = mocker.patch(
        'bot_app.handlers.admin_handlers.get_photo_description_by_file_id_from_db',
        return_value=description
    )

    mock_add_photo_with_category_to_db = mocker.patch(
        'bot_app.handlers.admin_handlers.add_photo_with_category_to_db',
        return_value=None
    )

    mock_delete_photo_from_db = mocker.patch(
        'bot_app.handlers.admin_handlers.delete_photo_from_db',
        return_value=None
    )

    mock_update_photo_description = mocker.patch(
        'bot_app.handlers.admin_handlers.update_photo_description',
        return_value=None
    )

    mock_update_photo_in_db = mocker.patch(
        'bot_app.handlers.admin_handlers.update_photo_in_db',
        return_value=None
    )

    # Тестируем сценарии для разных команд
    for command in command_data:

        # Проверяем команды с "ДА"
        callback.data = f'confirm_{command}_yes'

        # Данные для теста
        callback.message.caption = f'{category} {transliterated_text}'
        callback.message.transliterated_text = transliterated_text
        callback.message.photo[0].file_id = photo_id

        if command == 'add':
            state.get_data = AsyncMock(return_value={
                'photo_id': photo_id,
                'category': category,
                'description': description,
                'description_translit': transliterated_text
            })

            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )

            # Проверяем, что функция для получения описания фото была вызвана
            mock_get_photo_description_by_file_id_from_db.assert_awaited_once_with(
                pool=mock_pool,
                file_id=photo_id
            )

            # Проверяем, что функция добавления фото в БД была вызвана
            mock_add_photo_with_category_to_db.assert_awaited_once_with(
                pool=mock_pool,
                photo_id=photo_id,
                description=description,
                description_translit=transliterated_text,
                category_name=category
            )

            # Проверяем, что сообщение с текстом было успешно отправлено
            callback.message.edit_text.assert_awaited_once_with(text=LEXICON_RU['add_photo_confirm'])

            # Проверяем, что сброс состояний был вызван
            state.clear.assert_awaited_once()
            callback.message.edit_text.reset_mock()

            # Тестируем сценарий с ошибкой
            state.clear.reset_mock()
            mock_add_photo_with_category_to_db.side_effect = PhotoAlreadyExistsError()
            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )
            callback.message.answer.assert_awaited_once_with(
                f'⚠️ Фото с таким описанием уже существует в базе данных.\n\n'
                f'{LEXICON_RU["photo_already_exists_error"]}'
            )

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.message.answer.reset_mock()
            state.clear.reset_mock()
            mock_add_photo_with_category_to_db.side_effect = None

            mock_add_photo_with_category_to_db.side_effect = DatabaseAddPhotoWithCategoryError()
            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )
            callback.message.edit_text.assert_awaited_once_with(text=LEXICON_RU['error'])

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.message.edit_text.reset_mock()
            state.clear.reset_mock()
            mock_add_photo_with_category_to_db.side_effect = None

        elif command == 'delete':

            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )

            # Проверяем, что функция удаления фото из БД была вызвана
            mock_delete_photo_from_db.assert_awaited_once_with(
                pool=mock_pool,
                photo_id=photo_id
            )

            # Проверяем, что сообщение было удалено
            callback.message.delete.assert_awaited_once()
            # Проверяем, что сообщение с текстом было успешно отправлено
            callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['delete_photo_successful'])

            # Проверяем, что сброс состояний был вызван
            state.clear.assert_awaited_once()

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.message.answer.reset_mock()
            callback.message.delete.reset_mock()
            state.clear.reset_mock()

            # Тестируем сценарий с ошибкой
            mock_delete_photo_from_db.side_effect = DatabaseDeletePhotoError()
            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )
            callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.message.answer.reset_mock()
            state.clear.reset_mock()
            mock_delete_photo_from_db.side_effect = None

        elif command == 'update':

            # Проверяем, что вызов state.get_data был вызван
            state.get_data = AsyncMock(return_value={
                'photo_id': photo_id,
                'new_description': new_description,
                'new_description_translit': new_description_translit,
            })

            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )

            # Проверяем, что вызов state.get_data был вызван
            state.get_data.assert_awaited_once()

            # Проверяем, что функция обновления описания к фото в БД была вызвана
            mock_update_photo_description.assert_awaited_once_with(
                pool=mock_pool,
                photo_id=photo_id,
                new_description=new_description,
                new_description_translit=new_description_translit
            )

            # Проверяем, что сообщение с текстом было успешно отправлено
            callback.message.edit_caption.assert_awaited_once_with(
                caption=f'{LEXICON_RU["new_photo_description"]}\n'
                        f'<b>{new_description}</b>'
            )
            # Проверяем, что сброс состояний был вызван
            state.clear.assert_awaited_once()

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.message.edit_caption.reset_mock()
            state.clear.reset_mock()

            # Тестируем сценарий с ошибкой
            mock_update_photo_description.side_effect = DatabaseUpdatePhotoDescriptionError()
            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )
            callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.message.answer.reset_mock()
            mock_update_photo_description.side_effect = None

        elif command == 'replace':

            # Проверяем, что вызов state.get_data был вызван
            state.get_data = AsyncMock(return_value={
                'photo_id': photo_id,
                'new_photo_id': new_photo_id
            })

            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )

            # Проверяем, что вызов state.get_data был вызван
            state.get_data.assert_awaited_once()

            # Проверяем, что функция обновления фото в БД была вызвана
            mock_update_photo_in_db.assert_awaited_once_with(
                pool=mock_pool,
                photo_id=photo_id,
                new_photo_id=new_photo_id
            )

            # Проверяем, что сообщение с текстом было успешно отправлено
            callback.message.edit_caption.assert_awaited_once_with(caption=LEXICON_RU['update_photo_successful'])
            # Проверяем, что сброс состояний был вызван
            state.clear.assert_awaited_once()

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.message.edit_caption.reset_mock()
            state.clear.reset_mock()

            # Тестируем сценарий с ошибкой
            mock_update_photo_in_db.side_effect = DatabaseUpdatePhotoError()
            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )
            callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.message.answer.reset_mock()
            mock_update_photo_in_db.side_effect = None

        # Проверяем команды с "НЕТ"
        callback.data = f'confirm_{command}_no'

        if command == 'add':

            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )

            # Проверяем, что сообщение с текстом об отмене действия успешно отправлено
            callback.message.edit_text.assert_awaited_once_with(text=LEXICON_RU['cancel'])

            # Проверяем, что сброс состояний был вызван
            state.clear.assert_awaited_once()

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.message.edit_text.reset_mock()
            state.clear.reset_mock()

        elif command == 'delete':

            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )

            # Проверяем, что сообщение с описанием для фото успешно отправлено
            callback.message.edit_caption.assert_awaited_once_with(
                caption=f'{LEXICON_RU["photo_found"]} {description}'
            )

            # Проверяем, что сброс состояний был вызван
            state.clear.assert_awaited_once()

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.message.edit_caption.reset_mock()
            state.clear.reset_mock()

        elif command == 'update':

            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )

            # Проверяем, что сообщение с описанием для фото успешно отправлено
            callback.message.edit_caption.assert_awaited_once_with(
                caption=description
            )

            # Проверяем, что сброс состояний был вызван
            state.clear.assert_awaited_once()

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.message.edit_caption.reset_mock()
            state.clear.reset_mock()

        elif command == 'replace':

            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )

            # Проверяем, что сообщение с фото успешно удалено
            callback.message.delete.assert_awaited_once_with()

            # Проверяем, что сообщение с описанием для фото успешно отправлено
            callback.message.answer_photo.assert_awaited_once_with(
                photo=photo_id,
                caption=LEXICON_RU['update_photo_cancel']
            )

            # Проверяем, что сброс состояний был вызван
            state.clear.assert_awaited_once()

            # Сбрасываем отправку сообщения для тестирования других сценариев
            state.clear.reset_mock()
            state.get_data.reset_mock()

    # Мокаем данные в словаре data
    state.get_data = AsyncMock(return_value={
        'cancel_handler': True
    })

    # Запуск хендлера
    await process_confirm_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )

    # Проверяем, что в случае отмены будет отправлено сообщение с необходимым текстом
    callback.answer.assert_awaited_once_with(text=LEXICON_RU['buttons_not_active'])

    # Сбрасываем отправку сообщения для тестирования других сценариев
    callback.answer.reset_mock()
    state.get_data.reset_mock()

    state.get_data = AsyncMock(return_value={
        'cancel_handler': False
    })

    # Тестируем сценарий с ошибкой
    mock_get_photo_description_by_file_id_from_db.side_effect = DatabaseGetPhotoDescriptionByFileIdError()
    # Запуск хендлера
    await process_confirm_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

    # Сбрасываем отправку сообщения для тестирования других сценариев
    mock_get_photo_description_by_file_id_from_db.side_effect = None
    callback.message.answer.reset_mock()

    # Тестируем сценарий с ошибкой
    state.get_data = Exception()
    # Запуск хендлера
    await process_confirm_callback(
        callback=callback,
        state=state,
        pool=mock_pool
    )
    callback.message.answer.assert_awaited_once_with(text=LEXICON_RU['error'])

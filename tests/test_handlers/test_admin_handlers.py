import pytest

from unittest.mock import (
    MagicMock,
    AsyncMock,
    Mock
)

from bot_app.handlers.admin_handlers import (
    check_message_for_photo,
    process_delete_photo_callback,
    process_update_photo_description,
    update_photo_description_handler,
    process_confirm_callback,

)
from bot_app.lexicon.lexicon_common.lexicon_ru import LEXICON_RU
from bot_app.states.admin_states import AdminUpdateDescriptionState


@pytest.mark.asyncio
async def test_check_message_for_photo(mock_db_pool,
                                       mock_handler,
                                       mock_admin,
                                       keyboards_test_data,
                                       sample_test_data,
                                       mocker):

    """
    Тестирование хендлера добавления фото в БД пользователем.
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
    description = photo_data['description']
    category = photo_data['category']

    categories_data = sample_test_data['category']
    groups_data = sample_test_data['groups']

    user_data = sample_test_data['user']
    user_id = user_data['user_id']

    keyboard_confirmation = keyboards_test_data['confirmation_keyboard']

    # Получаем фикстуры
    message, callback, state = mock_handler
    mock_pool, mock_conn = await mock_db_pool(data=groups_data)
    mock_dp, _, mock_member = mock_admin

    # Настраиваем мок-объекты
    message.caption = f'{category} {description}'
    message.from_user.id = user_id

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
        new_callable=AsyncMock
    )

    # Мокаем функцию создания клавиатуры
    mock_create_admins_confirmation_keyboard = mocker.patch(
        'bot_app.handlers.admin_handlers.create_admins_confirmation_keyboard',
        return_value=keyboard_confirmation
    )

    # Если пользователь админ
    mock_member.is_chat_admin.return_value = True
    mock_check_is_admin.return_value = True

    # Запуск хендлера
    await check_message_for_photo(
        message=message,
        dp=mock_dp,
        pool=mock_pool
    )

    # Проверяем вызовы
    mock_get_categories_from_db.assert_called_once_with(pool=mock_pool)
    mock_get_groups_from_db.assert_called_once_with(pool=mock_pool)

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    message.answer.assert_awaited_once_with(
        text=f'{LEXICON_RU["add_photo_to_db"]} {description} '
             f'{LEXICON_RU["add_photo_category_to_db"]} {category}\n'
             f'{LEXICON_RU["confirm"]}',
        reply_markup=keyboard_confirmation
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_admins_confirmation_keyboard.assert_called_once()

    # Сбрасываем отправку сообщений для дальнейшего тестирования
    message.answer.reset_mock()
    mock_get_categories_from_db.reset_mock()
    mock_get_groups_from_db.reset_mock()
    mock_check_is_admin.reset_mock()

    # Если пользователь не админ
    mock_member.is_chat_admin.return_value = False
    mock_check_is_admin.return_value = False

    # Настраиваем мок-объекты
    message.caption = f'{category} {description}'

    # Запуск хендлера
    await check_message_for_photo(
        message=message,
        dp=mock_dp,
        pool=mock_pool
    )

    # Проверяем вызовы
    mock_get_categories_from_db.assert_called_once_with(pool=mock_pool)
    mock_get_groups_from_db.assert_called_once_with(pool=mock_pool)

    # Проверяем, что сообщение с текстом было успешно отправлено
    message.answer.assert_awaited_once_with(text=LEXICON_RU['user_not_admin'])

    # Сбрасываем отправку сообщений для дальнейшего тестирования
    message.answer.reset_mock()
    mock_get_categories_from_db.reset_mock()

    # Тестируем сценарий с ошибкой
    message.caption = None
    mock_get_categories_from_db.side_effect = Exception("Test Error")

    # Запуск хендлера
    await check_message_for_photo(
        message=message,
        dp=mocker.Mock(),
        pool=mock_pool
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    message.answer.assert_awaited_once_with(text=LEXICON_RU["error"])


@pytest.mark.asyncio
async def test_process_delete_photo_callback(mock_handler,
                                             keyboards_test_data,
                                             mocker):

    """
    Тестирование хендлера обработки нажатия кнопки "Удалить" пользователем.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :param keyboards_test_data: Словарь с тестовыми данными клавиатуры.
    :param mocker: Мокер для добавления side_effect в тест для тестирования ошибки.
    :return: Функция ничего не возвращает.
    """

    # Данные для теста
    keyboard_confirmation = keyboards_test_data['confirmation_keyboard']

    # Получаем фикстуры
    message, callback, state = mock_handler

    # Мокаем функцию создания клавиатуры
    mock_create_admins_confirmation_keyboard = mocker.patch(
        'bot_app.handlers.admin_handlers.create_admins_confirmation_keyboard',
        return_value=keyboard_confirmation
    )

    callback.message.caption = True

    # Запуск хендлера
    await process_delete_photo_callback(callback=callback)

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
    callback.answer.reset_mock()

    # Запуск хендлера
    await process_delete_photo_callback(callback=callback)

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.answer.assert_awaited_once_with(text=LEXICON_RU['error'])


@pytest.mark.asyncio
async def test_process_update_photo_description(mock_handler,
                                                keyboards_test_data,
                                                sample_test_data,
                                                ):

    """
    Тестирование хендлера редактирования описания фото в БД пользователем.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :param keyboards_test_data: Словарь с тестовыми данными клавиатуры.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    """

    # Данные для теста
    photo_data = sample_test_data['photo']
    photo_id = photo_data['photo_id']

    # Получаем фикстуры
    message, callback, state = mock_handler

    callback.message.photo = [Mock(file_id=photo_id)]

    callback.message.caption = True

    # Запуск хендлера
    await process_update_photo_description(
        callback=callback,
        state=state
    )

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    callback.message.edit_caption.assert_awaited_once_with(
        caption=LEXICON_RU['update_photo_description'],
        reply_markup=None
    )

    # Проверяем, что установлено состояние FSM
    state.set_state.assert_awaited_once_with(AdminUpdateDescriptionState.update_description)

    # Проверяем, что данные фото успешно обновляются в состоянии
    state.update_data.assert_called_once_with(photo_id=photo_id)

    # Тестируем сценарий с ошибкой
    callback.message.edit_caption.reset_mock()
    callback.message.caption = False

    # Запуск хендлера
    await process_update_photo_description(
        callback=callback,
        state=state
    )

    # Проверяем, что в случае ошибки будет отправлено сообщение с необходимым текстом
    callback.answer.assert_awaited_once_with(text=LEXICON_RU['error'])


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
    keyboard_confirmation = keyboards_test_data['confirmation_keyboard']

    state_data = sample_test_data['state']
    photo_id = state_data['photo_id']

    text_data = sample_test_data['text']
    text = text_data['text']
    transliterated_text = text_data['transliterated_text']

    # Получаем фикстуры
    message, callback, state = mock_handler

    message.text = text
    message.transliterated_text = transliterated_text

    # Мокаем функцию создания клавиатуры
    mock_create_admins_confirmation_keyboard = mocker.patch(
        'bot_app.handlers.admin_handlers.create_admins_confirmation_keyboard',
        return_value=keyboard_confirmation
    )

    # Проверяем, что вызов state.get_data был вызван
    state.get_data.return_value = state_data

    # Запуск хендлера
    await update_photo_description_handler(
        message=message,
        state=state
    )

    # Проверяем, что вызов state.get_data был вызван
    state.get_data.assert_called_once()

    # Проверяем, что данные фото успешно обновляются в состоянии
    state.update_data.assert_called_once_with(new_description=transliterated_text)

    # Проверяем, что сообщение с текстом и клавиатурой было успешно отправлено
    message.answer_photo.assert_awaited_once_with(
        photo=photo_id,
        caption=f'{LEXICON_RU["new_photo_description"]}'
                f'{transliterated_text}'
                f'{LEXICON_RU["confirm"]}',
        reply_markup=keyboard_confirmation
    )

    # Проверяем, что функция создания клавиатуры была вызвана с правильными параметрами
    mock_create_admins_confirmation_keyboard.assert_called_once()

    # Тестируем сценарий с ошибкой
    message.answer_photo.reset_mock()
    state.get_data.return_value = None

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
    new_description = state_data['new_description']

    command_data = sample_test_data['command']

    # Получаем фикстуры
    message, callback, state = mock_handler
    mock_pool, mock_conn = await mock_db_pool(data=photo_data)

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

    # Тестируем сценарии для разных команд
    for command in command_data:
        print(f'command: {command}')

        # Проверяем команды с "ДА"
        callback.data = f'confirm_{command}_yes'
        print(f'callback: {callback.data}')

        # Данные для теста
        callback.message.caption = f'{category} {transliterated_text}'
        callback.message.transliterated_text = transliterated_text
        callback.message.photo[0].file_id = photo_id

        if command == 'add':

            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )

            # Проверяем, что функция для получения описания фото была вызвана
            mock_get_photo_description_by_file_id_from_db.assert_called_once_with(
                pool=mock_pool,
                file_id=photo_id
            )

            # Проверяем, что функция добавления фото в БД была вызвана
            mock_add_photo_with_category_to_db.assert_called_once_with(
                pool=mock_pool,
                photo_id=photo_id,
                description=transliterated_text,
                category_name=category
            )

            # Проверяем, что сообщение с текстом было успешно отправлено
            callback.answer.assert_called_once_with(text=LEXICON_RU['add_photo_confirm'])

            # Проверяем, что сброс состояний был вызван
            state.clear.assert_called_once()

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.answer.reset_mock()
            state.clear.reset_mock()

        elif command == 'delete':

            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )

            # Проверяем, что функция удаления фото из БД была вызвана
            mock_delete_photo_from_db.assert_called_once_with(
                pool=mock_pool,
                photo_id=photo_id
            )

            # Проверяем, что сообщение было удалено
            callback.message.delete.assert_called_once()
            # Проверяем, что сообщение с текстом было успешно отправлено
            callback.answer.assert_called_once_with(text=LEXICON_RU['delete_photo_successful'])

            # Проверяем, что сброс состояний был вызван
            state.clear.assert_called_once()

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.answer.reset_mock()
            state.clear.reset_mock()

        elif command == 'update':

            # Проверяем, что вызов state.get_data был вызван
            state.get_data.return_value = state_data

            # Запуск хендлера
            await process_confirm_callback(
                callback=callback,
                state=state,
                pool=mock_pool
            )

            # Проверяем, что вызов state.get_data был вызван
            state.get_data.assert_called_once()

            # Проверяем, что функция обновления описания к фото в БД была вызвана
            mock_update_photo_description.assert_called_once_with(
                pool=mock_pool,
                photo_id=photo_id,
                new_description=new_description
            )

            # Проверяем, что сообщение с текстом было успешно отправлено
            callback.message.edit_caption.assert_called_once_with(
                caption=f'{LEXICON_RU["new_photo_description"]}'
                        f'{new_description}'
            )
            # Проверяем, что сброс состояний был вызван
            state.clear.assert_called_once()

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.message.edit_caption.reset_mock()
            state.clear.reset_mock()

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
            callback.answer.assert_called_once_with(LEXICON_RU['cancel'])

            # Проверяем, что сброс состояний был вызван
            state.clear.assert_called_once()

            # Сбрасываем отправку сообщения для тестирования других сценариев
            callback.answer.reset_mock()
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
            state.clear.assert_called_once()

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
            state.clear.assert_called_once()

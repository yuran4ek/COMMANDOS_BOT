import pytest

from aiogram.exceptions import TelegramBadRequest

from unittest.mock import (
    AsyncMock,
    MagicMock
)

from bot_app.utils.admin_check import check_is_admin


@pytest.mark.asyncio
async def test_check_is_admin(mock_admin,
                              sample_test_data):

    """
    Тестирование функции проверки пользователя на то, что он является админом в группах.
    :param mock_admin: Функция, возвращающая замокированные объекты bot и get_chat_member.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    """

    # Получаем данные для теста
    user_data = sample_test_data['user']
    user_id = user_data['user_id']

    groups_id = sample_test_data['groups']

    # Получаем данные из фикстур
    mock_bot, mock_member = mock_admin

    # Если пользователь админ
    mock_member.status = 'administrator'

    # Запуск функции
    result_is_admin = await check_is_admin(
        bot=mock_bot,
        user_id=user_id,
        groups_id=groups_id
    )

    # Проверка результата
    assert result_is_admin is True

    # Если пользователь не админ
    mock_member.status = 'member'

    # Запуск функции
    result_not_admin = await check_is_admin(
        bot=mock_bot,
        user_id=user_id,
        groups_id=groups_id
    )

    # Проверка результата
    assert result_not_admin is False

    # Тестируем функцию с исключением
    mock_member.get_chat_member = AsyncMock(side_effect=TelegramBadRequest(
        method=MagicMock(),
        message='Test Error'
    ))

    # Запуск функции
    result_error = await check_is_admin(
        bot=mock_bot,
        user_id=user_id,
        groups_id=groups_id
    )

    # Проверка результата
    assert result_error is False

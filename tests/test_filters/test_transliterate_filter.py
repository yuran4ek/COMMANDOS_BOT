import pytest

from transliterate import translit

from bot_app.filters.transliterate_filter import TransliterationFilter


@pytest.mark.asyncio
@pytest.mark.parametrize('input_text, mode, expected_translit',
                         [
                             ('Category123 Описание', 'add', 'Opisanie'),
                             ('Category123 Opisanie', 'add', 'Описание'),
                             ('Opisanie', 'update', 'Описание'),
                             ('Описание', 'update', 'Opisanie'),
                             ('123456789', 'add', None)
                         ]
                         )
async def test_transliterate_filter(mock_handler,
                                    input_text: str,
                                    mode: str,
                                    expected_translit: str | None) -> None:

    """
    Тестирование фильтра для преобразования текста из кириллицы в латиницу.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :param input_text: Строка с входными тестовыми данными.
    :param mode: Строка с описанием параметра для использования в логике фильтра.
    :param expected_translit: Строка с результатом.
    :return: Функция ничего не возвращает.
    """

    # Создаём объект фильтра
    translit_filter = TransliterationFilter(mode=mode)

    # Получаем фикстуры
    message, _, _ = mock_handler

    message.text = input_text

    # Запускаем фильтр
    result = await translit_filter(message)

    # Если True, то проверяем, что текст был изменён
    if expected_translit is not None:
        assert 'description_translit' in result
        assert result['description_translit'] == expected_translit
    else:
        assert 'description_translit' not in result

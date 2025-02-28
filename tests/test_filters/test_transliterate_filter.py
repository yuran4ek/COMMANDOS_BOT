import pytest

from transliterate import translit

from bot_app.filters.transliterate_filter import TransliterationFilter


@pytest.mark.asyncio
@pytest.mark.parametrize('input_text,'
                         'expected_output,'
                         'expected_result',
                         [('Привет', translit('Привет', 'ru', reversed=True), True),
                          ('Hello', 'Hello', True),
                          ('123456789', False, False)])
async def test_transliterate_filter(mock_handler,
                                    input_text: str,
                                    expected_output: str,
                                    expected_result: str) -> None:

    """
    Тестирование фильтра для преобразования текста из кириллицы в латиницу.
    :param mock_handler: Функция, возвращающая кортеж из мокированных объектов для message, callback и state.
    :param input_text: Строка с входными тестовыми данными.
    :param expected_output: Строка с выходными текстовыми данными.
    :param expected_result: Строка с результатом.
    :return: Функция ничего не возвращает.
    """

    # Вызываем тестируемый фильтр
    transliterate_filter = TransliterationFilter(transliterate=True)

    # Получаем фикстуры
    message, _, _ = mock_handler

    message.text = input_text

    # Запускаем фильтр
    result = await transliterate_filter.check(message)

    # Проверяем результат
    assert result == expected_result

    # Если True, то проверяем, что текст был изменён
    if expected_result:
        assert message.transliterated_text == expected_output
    else:
        assert not hasattr(message, 'transliterated_text')

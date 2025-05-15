import re

from aiogram.filters import BaseFilter
from transliterate import translit


def detect_language(text: str) -> str:

    """
    Определение языка текста (кириллица или латиница).
    :param text: Строка с текстом для определения языка.
    :return: Возвращает строку текста.
    """

    # Проверяем текст на содержание кириллицы
    if re.search(r'[а-яА-Я]', text):
        return 'cyrillic'
    # Проверяем текст на содержание латиницы
    elif re.search(r'[a-zA-Z]', text):
        return 'latin'
    return 'unknowm'


class TransliterationFilter(BaseFilter):

    """
    Класс для преобразования текста из кириллицы в латиницу.
    """

    def __init__(self, mode: str):

        """
        Передача параметра mode в __init__ для использования в фильтре.
        :param mode: Режим работы фильтра, например при добавлении или изменении описания фотографии.
        """
        self.mode = mode

    async def __call__(self, message) -> dict[str, str]:

        """
        Вызов фильтра для осуществления перевода текста.
        :param message: Сообщение от пользователя.
        :return: Функция возвращает словарь с оригинальным тестом и переводом этого текста на другой язык.
        """
        user_input = (message.text or message.caption or "").strip()

        # Определяем язык введённого сообщения
        language = detect_language(text=user_input)
        if self.mode == 'add':
            user_input_separate = ' '.join(user_input.split(' ')[1::])
        else:
            user_input_separate = user_input

        # Если язык - кириллица
        if language == 'cyrillic':
            # Добавляем трансформированный текст в объект message
            translit_text = translit(
                user_input_separate,
                language_code='ru',
                reversed=True
            )
        # Если язык - латиница
        elif language == 'latin':
            # Добавляем трансформированный текст в объект message
            translit_text = translit(
                user_input_separate,
                language_code='ru',
                reversed=False
            )
        else:
            # Если язык не определён
            return {'description': user_input_separate}

        return {
            'description': user_input_separate,
            'description_translit': translit_text
        }

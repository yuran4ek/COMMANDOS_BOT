import re

from aiogram.filters import BaseFilter
from transliterate import translit


def detect_language(text: str) -> str:

    """
    Определение языка текста (кириллица или латиница).
    :param text: Строка с текстом для определения языка
    :return: Возвращает строку текста
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

    key = 'transliterate'

    # Инициализируем переменную transliterate
    def __init__(self, transliterate):
        self.transliterate = transliterate

    # Функция для преобразования текста из кириллицы в латиницу
    async def check(self, message):
        user_input = getattr(message, 'text', '').strip() if message.text else None
        if not user_input:
            return False

        # Определяем язык введённого сообщения
        language = detect_language(text=user_input)
        if language == 'cyrillic':
            # Добавляем трансформированный текст в объект message
            message.transliterated_text = translit(
                user_input,
                language_code='ru',
                reversed=True
            )
            return True
        elif language == 'latin':
            message.transliterated_text = user_input
            return True

        return False

    async def __call__(self, message):
        return await self.check(message)

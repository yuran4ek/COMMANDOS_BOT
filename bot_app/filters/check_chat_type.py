from aiogram.filters.base import Filter
from aiogram.types import Message


class ChatTypeFilter(Filter):

    """
    Класс для определения типа чата для пользователя.
    """

    def __init__(self, chat_type: str):

        """
        Передача параметра chat_type в __init__ для использования в фильтре.
        :param chat_type: Тип чата, например 'private' для доступа к командам бота.
        """

        self.chat_type = chat_type

    async def __call__(self, message: Message) -> None:

        """
        Вызов фильтра для определения типа чата.
        :param message: Сообщение от пользователя.
        :return: Функция производит сравнение типа чата с задаваемым. Ничего не возвращает.
        """

        return message.chat.type == self.chat_type

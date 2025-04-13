import asyncpg.pool
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Update

from typing import (
    Callable,
    Dict,
    Any,
    Awaitable
)


class DatabaseMiddleware(BaseMiddleware):

    """
    Middleware для передачи pool в handlers.
    """

    def __init__(self, pool: asyncpg.pool.Pool):

        """
        Инициализация middleware с пулом соединения с БД.
        :param pool: Пул соединений с БД.
        """

        super().__init__()
        self.pool = pool

    async def __call__(self,
                       handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
                       event: Update,
                       data: Dict[str, Any]):

        """
        Переопределение метода __call__.
        :param handler: Хендлер, который должен быть вызван.
        :param event: Объект события Update.
        :param data: Словарь данных, передаваемый в хендлер.
        :return: Возвращает результат выполнения хендлера.
        """

        # Добавление pool в data
        data['pool'] = self.pool

        return await handler(event, data)

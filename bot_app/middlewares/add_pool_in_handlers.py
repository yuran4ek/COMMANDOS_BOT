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
    Middleware для передачи pool в handlers
    """

    def __init__(self, pool):
        super().__init__()
        self.pool = pool

    async def __call__(self,
                       handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
                       event: Update,
                       data: Dict[str, Any]):

        # Добавление pool в data
        data['pool'] = self.pool

        return await handler(event, data)

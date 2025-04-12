from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from config.log import logger


async def check_is_admin(bot: Bot,
                         user_id: int,
                         groups_id: list[int]) -> bool:

    """
    Проверка пользователя на то, что он является администратором в группах.
    :param bot: Объект Bot.
    :param user_id: ID проверяемого пользователя.
    :param groups_id: ID групп, в которых проверяется пользователь.
    :return:
    """

    # Осуществляем проверку по каждой группе из БД
    for group_id in groups_id:
        try:
            # Получаем информацию о пользователе в группе
            member = await bot.get_chat_member(
                group_id,
                user_id
            )
            # Если пользователь администратор
            if member.status in ['administrator', 'admin', 'creator']:
                return True
        except TelegramBadRequest:
            logger.error('Ошибка проверки пользователя на администратора в группах.')
            continue

    return False

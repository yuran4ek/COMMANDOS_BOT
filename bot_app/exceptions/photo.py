from .base import BotAppError


class PhotoAlreadyExistsError(BotAppError):
    """
    Фото с таким описанием уже существует в базе данных.
    """
    pass

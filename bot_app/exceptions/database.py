from .base import BotAppError


class DatabaseConnectionError(BotAppError):
    """
    Ошибка соединения с базой данных.
    """
    pass


class DatabaseAddGroupError(BotAppError):
    """
    Ошибка добавления группы в базу данных.
    """
    pass


class DatabaseGetGroupError(BotAppError):
    """
    Ошибка получения групп из базы данных.
    """
    pass


class DatabaseDeleteGroupError(BotAppError):
    """
    Ошибка удаления группы из базы данных.
    """
    pass


class DatabaseAddPhotoWithCategoryError(BotAppError):
    """
    Ошибка добавления фотографии с категорией в базу данных.
    """
    pass


class DatabaseGetPhotosError(BotAppError):
    """
    Ошибка получения фотографий из базы данных.
    """
    pass


class DatabaseGetTotalPhotosError(BotAppError):
    """
    Ошибка получения общего количества фотографий по категории из базы данных.
    """
    pass


class DatabaseGetPhotoDescriptionByFileIdError(BotAppError):
    """
    Ошибка получения описания фотографии по её file_id из базы данных.
    """
    pass


class DatabaseGetFileIdByDescriptionError(BotAppError):
    """
    Ошибка получения file_id фотографии по её описанию из базы данных.
    """
    pass


class DatabaseGetCategoriesError(BotAppError):
    """
    Ошибка получения всех категорий из базы данных.
    """
    pass


class DatabaseDeletePhotoError(BotAppError):
    """
    Ошибка удаления фотографии из базы данных.
    """
    pass


class DatabaseUpdatePhotoError(BotAppError):
    """
    Ошибка обновления фотографии в базе данных.
    """
    pass


class DatabaseUpdatePhotoDescriptionError(BotAppError):
    """
    Ошибка обновления описания фотографии в базе данных.
    """
    pass


class DatabaseSearchPhotoByDescriptionError(BotAppError):
    """
    Ошибка поиска фотографий по описанию в базе данных.
    """
    pass

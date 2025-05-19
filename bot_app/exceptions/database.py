from .base import BotAppError


class DatabaseConnectionError(BotAppError):
    """
    Ошибка соединения с БД>.
    """
    pass


class DatabaseAddGroupError(BotAppError):
    """
    Ошибка добавления группы в БД.
    """
    pass


class DatabaseGetGroupError(BotAppError):
    """
    Ошибка получения групп из БД.
    """
    pass


class DatabaseDeleteGroupError(BotAppError):
    """
    Ошибка удаления группы из БД.
    """
    pass


class DatabaseAddPhotoWithCategoryError(BotAppError):
    """
    Ошибка добавления фотографии с категорией в БД.
    """
    pass


class DatabaseGetPhotosError(BotAppError):
    """
    Ошибка получения фотографий из БД.
    """
    pass


class DatabaseGetTotalPhotosError(BotAppError):
    """
    Ошибка получения общего количества фотографий по категории из БД.
    """
    pass


class DatabaseGetPhotoDescriptionByFileIdError(BotAppError):
    """
    Ошибка получения описания фотографии по её file_id из БД.
    """
    pass


class DatabaseGetFileIdByDescriptionError(BotAppError):
    """
    Ошибка получения file_id фотографии по её описанию из БД.
    """
    pass


class DatabaseGetCategoriesError(BotAppError):
    """
    Ошибка получения всех категорий из БД.
    """
    pass


class DatabaseDeletePhotoError(BotAppError):
    """
    Ошибка удаления фотографии из БД.
    """
    pass


class DatabaseUpdatePhotoError(BotAppError):
    """
    Ошибка обновления фотографии в БД.
    """
    pass


class DatabaseUpdatePhotoDescriptionError(BotAppError):
    """
    Ошибка обновления описания фотографии в БД.
    """
    pass


class DatabaseSearchPhotoByDescriptionError(BotAppError):
    """
    Ошибка поиска фотографий по описанию в БД.
    """
    pass

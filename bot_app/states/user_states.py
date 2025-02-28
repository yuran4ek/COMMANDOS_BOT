from aiogram.fsm.state import (
    State,
    StatesGroup
)


class SearchPhotoState(StatesGroup):

    """
    Класс для хранения состояния при выборе поиска пользователем.
    """

    search_photo = State()


class SelectFromUserState(StatesGroup):

    """
    Класс для хранения состояний выбранной пользователем категории и текущей страницы.
    """

    category = State()
    current_page = State()

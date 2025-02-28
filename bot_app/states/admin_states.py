from aiogram.fsm.state import (
    State,
    StatesGroup
)


class AdminUpdateDescriptionState(StatesGroup):

    """
    Класс для хранения состояния при редактировании описания к фото администратором.
    """

    update_description = State()

from aiogram.fsm.state import (
    State,
    StatesGroup
)


class AdminUpdateDescriptionState(StatesGroup):

    """
    Класс для хранения состояния при редактировании описания к фото администратором.
    """

    update_description = State()
    update_photo = State()


class AdminAddPhotoState(StatesGroup):

    """
    Класс для хранения состояния при добавлении фото администратором.
    """

    add_photo = State()

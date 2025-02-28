from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import (
    InlineKeyboardBuilder,
    InlineKeyboardMarkup
)

from bot_app.lexicon.lexicon_common.lexicon_ru import (
    COMMANDS,
    LEXICON_RU
)

from config.config import BOT_URL_FOR_START


def create_link_button() -> InlineKeyboardMarkup:

    """
    Генерирует инлайн-кнопку с ссылкой на бота.
    :return: Возвращает объект инлайн-клавиатуры.
    """

    # Создаём объект клавиатуры
    kb_builder = InlineKeyboardBuilder()

    # Добавляем кнопку с ссылкой на бота
    kb_builder.button(
        text=LEXICON_RU['url_for_bot'],
        url=BOT_URL_FOR_START
    )

    return kb_builder.as_markup()


def create_categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:

    """
    Генерирует инлайн-клавиатуру из списка категорий.
    :param categories: Список категорий из БД.
    :return: Возвращает объект инлайн-клавиатуры.
    """

    # Создаём объект клавиатуры
    kb_builder = InlineKeyboardBuilder()

    # Добавляем кнопки из категорий
    for category in categories:
        kb_builder.button(
            text=category,
            callback_data=f"category_{category}"
        )

    # Указываем, что нужно по 2 кнопки в ряд
    kb_builder.adjust(2)

    # Добавляем кнопку поиска
    kb_builder.row(
        InlineKeyboardButton(
            text=COMMANDS['search_photo'],
            callback_data='search_photo'
        )
    )

    return kb_builder.as_markup()


def create_paginated_keyboard(current_page: int,
                              total_pages: int) -> InlineKeyboardMarkup:

    """
    Генерирует инлайн-клавиатуру с пагинацией.
    :param current_page: Текущая страница.
    :param total_pages: Общее количество фото.
    :return: Возвращает объект инлайн-клавиатуры с кнопками пагинации.
    """

    # Создаём объект клавиатуры
    kb_builder = InlineKeyboardBuilder()

    # Добавляем кнопки для пагинации
    pagination_buttons = []

    # Проверяем, что мы не на первой странице
    if current_page > 1:
        # Добавляем кнопку "Предыдущая страница"
        pagination_buttons.append(InlineKeyboardButton(
            text='◀',
            callback_data=f'page_{current_page - 1}')
        )

    # Текущая страница из общего количества страниц
    page_info = f"{current_page}/{total_pages}"

    # Проверяем, что мы не на последней странице
    if current_page < total_pages:
        # Вставляем информацию о странице как кнопку
        pagination_buttons.append(InlineKeyboardButton(
            text=page_info,
            callback_data="page_info")
        )
        # Добавляем кнопку "Следующая страница"
        pagination_buttons.append(InlineKeyboardButton(
            text='▶',
            callback_data=f'page_{current_page + 1}')
        )

    # Создаём клавиатуру
    if pagination_buttons:
        kb_builder.row(*pagination_buttons)

        kb_builder.row(
            InlineKeyboardButton(
                text=COMMANDS['search_photo'],
                callback_data='search_photo'
            )
        )

    return kb_builder.as_markup()


def create_admins_keyboard() -> InlineKeyboardMarkup:

    """
    Генерирует инлайн-клавиатуру только для администраторов.
    :return: Возвращает объект инлайн-клавиатуры.
    """

    # Создаём объект клавиатуры
    kb_builder = InlineKeyboardBuilder()

    # Добавляем кнопки "Удалить" и "Редактировать описание"
    kb_builder.button(
        text=COMMANDS['delete_photo'],
        callback_data='delete_photo'
    )
    kb_builder.button(
        text=COMMANDS['update_description'],
        callback_data='update_description'
    )

    # Указываем, что нужно по 2 кнопки в ряд
    kb_builder.adjust(2)

    return kb_builder.as_markup()


def create_admins_confirmation_keyboard(command: str) -> InlineKeyboardMarkup:

    """
    Генерирует инлайн-клавиатуру для подтверждения операции.
    :param command: Команда для подтверждения операции.
    :return: Возвращает объект инлайн-клавиатуры.
    """

    # Создаём объект клавиатуры
    kb_builder = InlineKeyboardBuilder()

    # Добавляем кнопки "Да" и "Нет"
    kb_builder.button(
        text=COMMANDS['yes'],
        callback_data=f'confirm_{command}_yes'
    )
    kb_builder.button(
        text=COMMANDS['no'],
        callback_data=f'confirm_{command}_no'
    )

    # Указываем, что нужно по 2 кнопки в ряд
    kb_builder.adjust(2)

    return kb_builder.as_markup()

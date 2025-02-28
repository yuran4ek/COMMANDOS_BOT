import math
import re

import asyncpg.pool
from aiogram import (
    Router,
    Dispatcher,
    F
)
from aiogram.types import (
    Message,
    CallbackQuery
)
from aiogram.fsm.context import FSMContext

from bot_app.filters.transliterate_filter import TransliterationFilter
from bot_app.keyboards.keyboards import (
    create_paginated_keyboard,
    create_admins_keyboard
)
from bot_app.lexicon.lexicon_common.lexicon_ru import LEXICON_RU
from bot_app.states.user_states import SearchPhotoState
from bot_app.utils.admin_check import check_is_admin

from config.database import (
    get_groups_from_db,
    get_photos_from_db,
    get_total_photos_count,
    get_photo_description_by_file_id_from_db,
    search_photo_by_description_in_db
)
from config.log import logger


# Создаём роутер для всех хендлеров, связанных с функциями пользователей
bot_user_handlers_router = Router(name='bot_user_handlers_router')


@bot_user_handlers_router.message(SearchPhotoState.search_photo,
                                  TransliterationFilter)
async def search_photo_handler(message: Message,
                               state: FSMContext,
                               pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий по состоянию поиска фото из FSM.
    :param message: Сообщение от пользователя.
    :param state: Состояние пользователя для FSM.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """
    try:
        # Преобразуем текст, если он на кириллице
        transformed_description = getattr(message, 'transliterated_text', message.text)
        # Выполняем поиск фото в БД по описанию от пользователя
        search_photo = await search_photo_by_description_in_db(
            pool=pool,
            query=transformed_description
        )
        # Если фото не найдено в БД
        if not search_photo:
            # Уведомляем пользователя о том, что ничего не найдено
            await message.answer(text=LEXICON_RU['photo_not_found'])
            return
        # Если фото найдено в БД
        else:
            for photo in search_photo:
                # Получаем данные фото
                photo_id = photo['photo_id']
                description = photo['description']
                category = photo['category']
                # Отправляем пользователю все найденные фото с описанием и категорией
                await message.answer_photo(
                    photo=photo_id,
                    caption=f'{LEXICON_RU["photo_found"]} {description} из категории {category}'
                )
            # Очищаем состояние для дальнейшего его использования
            await state.clear()
    except Exception as e:
        logger.error(f'Ошибка при обработке сообщения от пользователя при поиске фото: {e}')
        await message.answer(LEXICON_RU['error'])


@bot_user_handlers_router.callback_query(F.data == 'search_photo')
async def search_photo_callback(callback: CallbackQuery,
                                state: FSMContext):

    """
    Хендлер, срабатывающий на команду с кнопки "Поиск".
    :param callback: CallbackQuery от пользователя с параметром поиска.
    :param state: Состояние пользователя для FSM.
    :return: Функция ничего не возвращает.
    """

    try:
        # Отправляем пользователю сообщение с инструкцией по поиску фото
        await callback.message.answer(text=LEXICON_RU['search_photo'])
        # Убираем "часики"
        await callback.answer()
        # Переходим в состояние FSM для поиска фото
        await state.set_state(SearchPhotoState.search_photo)
    except Exception as e:
        logger.error(f'Ошибка при обработке кнопки поиска: {e}')
        await callback.message.answer(LEXICON_RU['error'])


@bot_user_handlers_router.callback_query(F.data.startswith('category_'))
async def category_selection_callback(callback: CallbackQuery,
                                      state: FSMContext,
                                      pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий на команду с кнопки "Категория".
    :param callback: CallbackQuery от пользователя с параметром о категории.
    :param state: Состояние пользователя для FSM.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Получаем выбранную пользователем категорию
        category = callback.data.replace('category_', '')

        # Устанавливаем начальную страницу и значения для пагинации о максимальном выводе элементов на странице
        current_page = 1
        items_per_page = 5

        # Обновляем данные в словаре data, добавляя информацию о выбранной категории и текущей странице
        await state.update_data(
            category=category,
            current_page=current_page
        )

        # Получаем список сборок по категории и с пагинацией
        builds = await get_photos_from_db(
            pool=pool,
            category=category,
            limit=items_per_page,
            offset=(current_page - 1) * items_per_page
        )
        # Получаем общее количество доступных сборок по данной категории
        total_builds = await get_total_photos_count(
            pool=pool,
            category=category
        )

        # Рассчитываем общее количество страниц
        total_pages = math.ceil(total_builds / items_per_page)

        # Формируем сообщение с нумерацией сборок
        message_text = f'Выберите сборку из категории {category}:\n'
        for idx, build in enumerate(builds, start=1):
            message_text += f'{idx}. <a href="{build["photo_id"]}">{build["description"]}</a>\n'

        # Отправляем пользователю страницу со сборками и кнопками пагинации
        await callback.message.edit_text(
            text=message_text,
            reply_markup=create_paginated_keyboard(
                current_page=current_page,
                total_pages=total_pages
            )
        )
    except Exception as e:
        logger.error(f'Ошибка при обработке категории: {e}')
        await callback.message.answer(text=LEXICON_RU['error'])


@bot_user_handlers_router.callback_query(F.data.startswith('page_'))
async def process_pagination_callback(callback: CallbackQuery,
                                      state: FSMContext,
                                      pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий на переход по страницам.
    :param callback: CallbackQuery от пользователя с параметрами о текущей странице и категории.
    :param state: Состояние пользователя для FSM.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Получаем словарь с состоянием категории и кнопки пагинации
        data = await state.get_data()

        # Извлекаем номер страницы, если пусто, то устанавливаем 1
        current_page = data.get('current_page', 1)

        # Извлекаем категорию
        category = data.get('category')

        # Задаём общее количество элементов на странице
        items_per_page = 5

        # Получаем список сборок по категории и с пагинацией
        builds = await get_photos_from_db(
            pool=pool,
            category=category,
            limit=items_per_page,
            offset=(current_page - 1) * items_per_page
        )

        # Получаем общее количество доступных сборок по данной категории
        total_builds = await get_total_photos_count(
            pool=pool,
            category=category
        )

        # Рассчитываем общее количество страниц
        total_pages = math.ceil(total_builds / items_per_page)

        # Формируем сообщение с нумерацией сборок
        message_text = f'Выберите сборку из категории {category}:\n'
        for idx, build in enumerate(builds, start=1):
            message_text += f'{idx}. <a href="{build["photo_id"]}">{build["description"]}</a>\n'

        # Обновляем состояние с текущей страницей
        await state.update_data(current_page=current_page)

        # Отправляем пользователю страницу со сборками и кнопками пагинации
        await callback.message.edit_text(
            text=message_text,
            reply_markup=create_paginated_keyboard(
                current_page=current_page,
                total_pages=total_pages
            )
        )
    except Exception as e:
        logger.error(f'Ошибка при переходе на новую страницу: {e}')
        await callback.message.answer(text=LEXICON_RU['error'])


@bot_user_handlers_router.message()
async def send_photo_handler(message: Message,
                             dp: Dispatcher,
                             state: FSMContext,
                             pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий на переход по ссылке из сообщения со сборками.
    :param message: Сообщение от пользователя.
    :param dp: Объект Dispatcher.
    :param state: Состояние пользователя дл FSM.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    # Получаем данные о пользователе
    user_id = message.from_user.id
    # Получаем группы из БД
    groups_id = await get_groups_from_db(pool=pool)

    try:
        # Проверяем, содержится ли ссылка на фото в сообщении от пользователя
        match = re.search(r'AgACAgIAAxkBAAEB[\dA-Za-z_-]+', message.text)

        # Если содержится
        if match:
            # Извлекаем file_id
            photo_id = match.group(0)

            # Получаем описание из базы данных по file_id
            description = LEXICON_RU['photo_found'] + await get_photo_description_by_file_id_from_db(
                pool=pool,
                file_id=photo_id
            )

            # Если пользователь не администратор
            if not await check_is_admin(
                dp=dp,
                user_id=user_id,
                groups_id=groups_id
            ):
                # Отправляем фотографию с описанием
                await message.answer_photo(
                    photo_id,
                    caption=description
                )

                # Очищаем состояние для дальнейшего его использования
                await state.clear()
            else:
                # Отправляем фотографию с описанием и кнопками "Удалить" и "Изменить описание"
                await message.answer_photo(
                    photo_id,
                    caption=description,
                    reply_markup=create_admins_keyboard()
                )

    except Exception as e:
        logger.error(f'Ошибка при обработке сообщения от пользователя с ссылкой на фото: {e}')
        await message.answer(text=LEXICON_RU['error'])

import math

import asyncpg.pool
from aiogram import (
    Router,
    Bot,
    F
)
from aiogram.types import (
    Message,
    CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardMarkup

from bot_app.exceptions.database import (
    DatabaseGetGroupError,
    DatabaseGetPhotosError,
    DatabaseGetTotalPhotosError,
    DatabaseGetFileIdByDescriptionError,
    DatabaseSearchPhotoByDescriptionError,
    DatabaseGetCategoriesError
)
from bot_app.keyboards.keyboards import (
    create_paginated_keyboard,
    create_categories_keyboard,
    create_admins_keyboard,
    create_assembl_buttons
)
from bot_app.lexicon.lexicon_common.lexicon_ru import LEXICON_RU
from bot_app.states.user_states import (SearchPhotoState)
from bot_app.utils.admin_check import check_is_admin

from config.database import (
    get_groups_from_db,
    get_categories_from_db,
    get_photos_from_db,
    get_total_photos_count,
    get_photo_file_id_by_description_from_db,
    search_photo_by_description_in_db
)
from config.log import logger


# Создаём роутер для всех хендлеров, связанных с функциями пользователей
bot_user_handlers_router = Router(name='bot_user_handlers_router')


@bot_user_handlers_router.message(SearchPhotoState.search_photo)
async def search_photo_handler(message: Message,
                               state: FSMContext,
                               bot: Bot,
                               pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий по состоянию поиска фото из FSM.
    :param message: Сообщение от пользователя.
    :param state: Состояние пользователя для FSM.
    :param bot: Объект Bot.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """
    try:
        # Получаем ID пользователя
        user_id = message.from_user.id

        # Получаем группы из БД
        groups_id = await get_groups_from_db(pool=pool)

        # Получаем категорию из словаря data
        data = await state.get_data()
        category = data.get('category')

        # Проверяем, является ли пользователь администратором
        is_admin = await check_is_admin(
            bot=bot,
            user_id=user_id,
            groups_id=groups_id
        )

        # Выполняем поиск фото в БД по описанию от пользователя
        search_photo = await search_photo_by_description_in_db(
            pool=pool,
            category=category,
            query=message.text
        )

        # Если фото найдено в БД
        if search_photo:
            if len(search_photo) > 1:
                await message.answer(
                    text=LEXICON_RU['search_result'],
                    reply_markup=create_assembl_buttons(assembl=search_photo)
                )
            else:
                for photo in search_photo:
                    # Получаем данные фото
                    photo_id = photo['photo_id']
                    description = photo['description']

                    if is_admin:
                        # Отправляем пользователю все найденные фото с описанием, категорией и клавиатурой
                        await message.answer_photo(
                            photo=photo_id,
                            caption=f'{LEXICON_RU["photo_found"]} <b>{description}</b>',
                            reply_markup=create_admins_keyboard(category=category)
                        )
                        await state.update_data(
                            photo_id=photo_id,
                            description=description
                        )

                    else:
                        # Отправляем пользователю все найденные фото с описанием и категорией
                        await message.answer_photo(
                            photo=photo_id,
                            caption=f'{LEXICON_RU["photo_found"]} <b>{description}</b>',
                            reply_markup=None
                        )
                        # Очищаем состояние для дальнейшего его использования
                        await state.clear()
        # Если фото не найдено в БД
        else:
            # Уведомляем пользователя о том, что ничего не найдено
            await message.answer(text=LEXICON_RU['photo_not_found'])
            return
    except DatabaseGetGroupError as e:
        logger.error(e)
        await message.answer(text=LEXICON_RU['error'])
    except DatabaseSearchPhotoByDescriptionError as e:
        logger.error(e)
        await message.answer(text=LEXICON_RU['error'])
    except Exception as e:
        logger.error(f'Ошибка при обработке сообщения от пользователя при поиске фото: {e}')
        await message.answer(text=LEXICON_RU['error'])


@bot_user_handlers_router.callback_query(F.data == 'search_photo')
async def search_photo_callback(callback: CallbackQuery,
                                state: FSMContext,
                                pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий на команду с кнопки "Поиск".
    :param callback: CallbackQuery от пользователя с параметром поиска.
    :param state: Состояние пользователя для FSM.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Проверяем, не вызвана ли команда /cancel
        data = await state.get_data()
        if not data.get('cancel_handler'):

            # Получаем категорию из словаря data
            category_data = data.get('category')
            categories = await get_categories_from_db(pool=pool)

            category = next((item['description'] for item in categories if item['name'] == category_data), None)

            # Отправляем пользователю сообщение с инструкцией по поиску фото
            await callback.message.edit_text(
                text=f'{LEXICON_RU["search_photo"]} <b>{category}</b>',
                reply_markup=None
            )
            # Убираем "часики"
            await callback.answer()
            # Переходим в состояние FSM для поиска фото
            await state.set_state(SearchPhotoState.search_photo)
        else:
            await callback.answer(text=LEXICON_RU['buttons_not_active'])
            return
    except DatabaseGetCategoriesError as e:
        logger.error(e)
        await callback.message.answer(text=LEXICON_RU['error'])
    except Exception as e:
        logger.error(f'Ошибка при обработке кнопки поиска: {e}')
        await callback.message.answer(text=LEXICON_RU['error'])


@bot_user_handlers_router.callback_query(F.data.startswith('move_back_to_category'))
async def move_back_to_category_callback(callback: CallbackQuery,
                                         state: FSMContext,
                                         pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий на команду с кнопки "Вернуться к категориям".
    :param callback: CallbackQuery от пользователя с параметром о категории.
    :param state: Состояние пользователя для FSM.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Проверяем, не вызвана ли команда /cancel
        data = await state.get_data()
        if not data.get('cancel_handler'):
            # Устанавливаем флаг False для активации кнопок
            await state.update_data(cancel_handler=False)
            # Получаем категории из БД
            categories = await get_categories_from_db(pool=pool)

            keyboard = create_categories_keyboard(categories=categories)

            # Отправляем пользователю кнопки с категориями
            await callback.message.edit_text(
                text=LEXICON_RU['assembl'],
                reply_markup=keyboard
                )
        else:
            await callback.answer(text=LEXICON_RU['buttons_not_active'])
            return
    except DatabaseGetCategoriesError as e:
        logger.error(e)
        await callback.message.answer(text=LEXICON_RU['error'])
    except Exception as e:
        logger.error(f'Ошибка при обработке кнопки "Назад": {e}')
        await callback.message.answer(text=LEXICON_RU['error'])


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
        # Проверяем, не вызвана ли команда /cancel
        data = await state.get_data()
        if not data.get('cancel_handler'):
            # Получаем выбранную пользователем категорию
            category = callback.data.replace('category_', '')

            # Устанавливаем начальную страницу и значения для пагинации о максимальном выводе элементов на странице
            current_page = 1
            items_per_page = 6

            # Обновляем данные в словаре data, добавляя информацию о выбранной категории и текущей странице
            await state.update_data(
                category=category,
                current_page=current_page
            )

            # Получаем список сборок по категории и с пагинацией
            assembl = await get_photos_from_db(
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

            # Генерируем клавиатуру со сборками
            assembl_kb = create_assembl_buttons(assembl=assembl)

            # Генерируем клавиатуру с пагинацией
            pagination_kb = create_paginated_keyboard(
                current_page=current_page,
                total_pages=total_pages
            )

            # Формируем сообщение с нумерацией сборок
            message_text = f'{LEXICON_RU["choose_assembl"]} <b>{category}</b>:\n'

            if not assembl:
                # Отправляем сообщение о том, что сборок в категории нет
                await callback.message.edit_text(
                    text=LEXICON_RU['empty_category']
                )
            else:
                # Если сообщение с фото
                if callback.message.photo:
                    await callback.message.delete()
                    await callback.message.answer(
                        text=message_text,
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=assembl_kb.inline_keyboard + pagination_kb.inline_keyboard
                        )
                    )
                else:
                    # Отправляем пользователю страницу со сборками и кнопками пагинации
                    await callback.message.edit_text(
                        text=message_text,
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=assembl_kb.inline_keyboard + pagination_kb.inline_keyboard
                        )
                    )
        else:
            await callback.answer(text=LEXICON_RU['buttons_not_active'])
            return
    except DatabaseGetPhotosError as e:
        logger.error(e)
        await callback.message.answer(text=LEXICON_RU['error'])
    except DatabaseGetTotalPhotosError as e:
        logger.error(e)
        await callback.message.answer(text=LEXICON_RU['error'])
    except Exception as e:
        logger.error(f'Ошибка при получении сборок по категории: {e}')
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
        # Проверяем, не вызвана ли команда /cancel
        data = await state.get_data()
        if not data.get('cancel_handler'):

            # Извлекаем номер страницы
            current_page = callback.data.split('_')[1]
            if current_page == 'info':
                await callback.answer()
                return
            else:
                current_page = int(current_page)

            # Извлекаем категорию
            category = data.get('category')

            # Задаём общее количество элементов на странице
            items_per_page = 6

            # Получаем список сборок по категории и с пагинацией
            assembl = await get_photos_from_db(
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

            # Генерируем клавиатуру со сборками
            assembl_kb = create_assembl_buttons(assembl=assembl)

            # Генерируем клавиатуру с пагинацией
            pagination_kb = create_paginated_keyboard(
                current_page=current_page,
                total_pages=total_pages
            )

            # Формируем сообщение с нумерацией сборок
            message_text = f'{LEXICON_RU["choose_assembl"]} <b>{category}</b>:\n'

            # Обновляем состояние с текущей страницей
            await state.update_data(current_page=current_page)

            # Отправляем пользователю страницу со сборками и кнопками пагинации
            await callback.message.edit_text(
                text=message_text,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=assembl_kb.inline_keyboard + pagination_kb.inline_keyboard
                )
            )
        else:
            await callback.answer(text=LEXICON_RU['buttons_not_active'])
            return
    except DatabaseGetPhotosError as e:
        logger.error(e)
        await callback.message.answer(text=LEXICON_RU['error'])
    except DatabaseGetTotalPhotosError as e:
        logger.error(e)
        await callback.message.answer(text=LEXICON_RU['error'])
    except Exception as e:
        logger.error(f'Ошибка при переходе на новую страницу: {e}')
        await callback.message.answer(text=LEXICON_RU['error'])


@bot_user_handlers_router.callback_query(F.data.startswith('photo_'))
async def send_photo_handler(callback: CallbackQuery,
                             bot: Bot,
                             state: FSMContext,
                             pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий на переход по сборке.
    :param callback: CallbackQuery от пользователя с информацией о текущей сборке.
    :param bot: Объект Bot.
    :param state: Состояние пользователя для FSM.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Проверяем, не вызвана ли команда /cancel
        data = await state.get_data()
        if not data.get('cancel_handler'):
            # Получаем данные о пользователе
            user_id = callback.from_user.id

            # Получаем группы из БД
            groups_id = await get_groups_from_db(pool=pool)

            caption = callback.data.replace("photo_", "")

            # Получаем категорию из словаря data
            category = data.get('category')

            # Получаем file_id из БД
            photo_id = await get_photo_file_id_by_description_from_db(
                pool=pool,
                description=caption
            )

            if not photo_id:
                await callback.message.edit_text(text=LEXICON_RU['error'])
                return

            # Получаем описание
            description = f'{LEXICON_RU["photo_found"]} <b>{caption}</b>'

            # Проверяем, является ли пользователь администратором в одной из групп
            is_admin = await check_is_admin(
                bot=bot,
                user_id=user_id,
                groups_id=groups_id
            )

            # Если пользователь не администратор
            if not is_admin:
                # Удаляем предыдущее сообщение
                # await callback.message.delete()
                # Отправляем фотографию с описанием
                await callback.message.answer_photo(
                    photo=photo_id,
                    caption=description
                )

                # Очищаем состояние для дальнейшего его использования
                await state.clear()
            else:
                # Удаляем предыдущее сообщение
                await callback.message.delete()
                # Сохраняем file_id в FSM
                await state.update_data(
                    photo_id=photo_id,
                    description=caption
                )
                # Отправляем фотографию с описанием и кнопками "Удалить" и "Изменить описание"
                await callback.message.answer_photo(
                    photo=photo_id,
                    caption=description,
                    reply_markup=create_admins_keyboard(category=category)
                )
            # Убираем "часики" на кнопке
            await callback.answer()
        else:
            await callback.answer(text=LEXICON_RU['buttons_not_active'])
            return
    except DatabaseGetGroupError as e:
        logger.error(e)
        await callback.message.answer(text=LEXICON_RU['error'])
    except DatabaseGetFileIdByDescriptionError as e:
        logger.error(e)
        await callback.message.answer(text=LEXICON_RU['error'])
    except Exception as e:
        logger.error(f'Ошибка при обработке сообщения от пользователя с ссылкой на фото: {e}')
        await callback.message.answer(text=LEXICON_RU['error'])

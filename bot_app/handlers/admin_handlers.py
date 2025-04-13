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

from bot_app.filters.transliterate_filter import TransliterationFilter
from bot_app.keyboards.keyboards import create_admins_confirmation_keyboard
from bot_app.lexicon.lexicon_common.lexicon_ru import LEXICON_RU
from bot_app.states.admin_states import AdminUpdateDescriptionState

from bot_app.utils.admin_check import check_is_admin

from config.database import (
    get_groups_from_db,
    get_categories_from_db,
    add_photo_with_category_to_db,
    delete_photo_from_db,
    update_photo_in_db,
    update_photo_description,
    get_photo_description_by_file_id_from_db
)
from config.log import logger


# Создаём роутер для всех хендлеров, связанных с функциями администратора
bot_admins_handlers_router = Router(name='bot_admins_handlers_router')


@bot_admins_handlers_router.message(F.photo,
                                    AdminUpdateDescriptionState.update_photo)
async def update_photo_handler(message: Message,
                               bot: Bot,
                               pool: asyncpg.pool.Pool,
                               state: FSMContext):

    """
    Хендлер, срабатывающий на состояние в FSM для замены сборки.
    :param message: Сообщение от пользователя.
    :param bot: Объект Bot.
    :param pool: Пул соединения с БД.
    :param state: Состояние пользователя для FSM.
    :return: Функция ничего не возвращает.
    """

    try:
        # Проверяем, не вызвана ли команда /cancel
        data = await state.get_data()
        if not data.get('cancel_handler'):
            # Получаем группы из БД
            groups_id = await get_groups_from_db(pool=pool)

            # Получаем ID пользователя
            user_id = message.from_user.id
            # Проверяем, является ли пользователь администратором в одной из групп
            if not await check_is_admin(
                    bot=bot,
                    user_id=user_id,
                    groups_id=groups_id
            ):
                await message.answer(text=LEXICON_RU['user_not_admin'])
                return

            # Получаем новый file_id
            new_photo_id = message.photo[-1].file_id
            # Получаем данные из словаря data
            category = data.get('category')
            photo_id = data.get('photo_id')

            # Получаем описание для фото из БД
            description = await get_photo_description_by_file_id_from_db(
                pool=pool,
                file_id=photo_id
            )

            # Сохраняем новый file_id в FSM
            await state.update_data(new_photo_id=new_photo_id)
            # Отправляем сообщение пользователю с информацией об описании и категории для фото и ждём
            # подтверждения от пользователя на замену фото в БД
            await message.answer_photo(
                photo=new_photo_id,
                caption=f'{LEXICON_RU["update_photo_in_db"]} {description} '
                        f'{LEXICON_RU["add_photo_category_to_db"]} {category}\n'
                        f'{LEXICON_RU["confirm"]}',
                reply_markup=create_admins_confirmation_keyboard(command='replace')
            )

    except Exception as e:
        logger.error(f'Ошибка при получении фото на замену его в БД: {e}')
        await message.answer(text=LEXICON_RU['error'])


@bot_admins_handlers_router.message(F.photo)
async def check_message_for_photo(message: Message,
                                  bot: Bot,
                                  pool: asyncpg.pool.Pool,
                                  state: FSMContext):

    """
    Хендлер, срабатывающий лишь на фотографию (в группах или ЛС администраторов групп)
    и описанием, которое начинается как одна из категорий.
    :param message: Сообщение от пользователя.
    :param bot: Объект Bot.
    :param pool: Пул соединения с БД.
    :param state: Состояние пользователя для FSM.
    :return: Функция ничего не возвращает.
    """

    try:
        # Устанавливаем флаг False для активации кнопок
        await state.update_data(cancel_handler=False)

        # Создаём объект фильтра
        translit_filter = TransliterationFilter(mode='add')
        # Получаем категории, группы из БД
        categories = await get_categories_from_db(pool=pool)
        groups_id = await get_groups_from_db(pool=pool)

        # Получаем ID пользователя
        user_id = message.from_user.id
        # Проверяем, является ли пользователь администратором в одной из групп
        if not await check_is_admin(
                bot=bot,
                user_id=user_id,
                groups_id=groups_id
        ):
            await message.answer(text=LEXICON_RU['user_not_admin'])
            return

        # Разбиваем строку входящего сообщения на подстроки, если сообщение не пустое
        caption_split = message.caption.split(maxsplit=1) if message.caption else []
        transliterated_text = await translit_filter(message)

        # Проверяем длину сообщения, и, если больше одного слова и сообщение начинается с одной из категорий
        for category in categories:
            if len(caption_split) > 1 and caption_split[0] in category['name']:
                # Получаем file_id
                photo_id = message.photo[-1].file_id
                # Сохраняем file_id в FSM
                await state.update_data(
                    photo_id=photo_id,
                    category=caption_split[0],
                    description=transliterated_text.get('description'),
                    description_translit=transliterated_text.get('description_translit')
                )
                # Отправляем сообщение пользователю с информацией об описании и категории для фото и ждём
                # подтверждения от пользователя на добавление фото с описанием в БД
                await message.answer(
                    text=f'{LEXICON_RU["add_photo_to_db"]} {caption_split[1]} '
                         f'{LEXICON_RU["add_photo_category_to_db"]} {caption_split[0]}\n'
                         f'{LEXICON_RU["confirm"]}',
                    reply_markup=create_admins_confirmation_keyboard(command='add')
                )

    except Exception as e:
        logger.error(f'Ошибка при получении фото на добавление в БД: {e}')
        await message.answer(text=LEXICON_RU['error'])


@bot_admins_handlers_router.callback_query(F.data == 'delete_photo')
async def process_delete_photo_callback(callback: CallbackQuery,
                                        state: FSMContext):

    """
    Хендлер, срабатывающий на команду с кнопки "Удалить сборку".
    :param callback: CallbackQuery от пользователя с параметром для удаления.
    :param state: Состояние пользователя для FSM.
    :return: Функция ничего не возвращает.
    """

    try:
        # Проверяем, не вызвана ли команда /cancel
        data = await state.get_data()
        if not data.get('cancel_handler'):
            # Если нет описания к фото
            if not callback.message.caption:
                raise Exception

            # Редактируем описание для фотографии
            await callback.message.edit_caption(
                caption=LEXICON_RU['delete_photo'],
                reply_markup=create_admins_confirmation_keyboard(command='delete')
            )
            # Убираем "часики" на кнопке
            await callback.answer()
        else:
            await callback.answer(text=LEXICON_RU['buttons_not_active'])
            return
    except Exception as e:
        logger.error(f'Ошибка при обработке запроса на удаление фото: {e}')
        await callback.answer(text=LEXICON_RU['error'])


@bot_admins_handlers_router.callback_query(F.data == 'update_photo')
async def process_delete_photo_callback(callback: CallbackQuery,
                                        state: FSMContext):

    """
    Хендлер, срабатывающий на команду с кнопки "Заменить сборку".
    :param callback: CallbackQuery от пользователя с параметром для удаления.
    :param state: Состояние пользователя для FSM.
    :return: Функция ничего не возвращает.
    """

    try:
        # Проверяем, не вызвана ли команда /cancel
        data = await state.get_data()
        if not data.get('cancel_handler'):
            # Если нет описания к фото
            if not callback.message.caption:
                raise Exception

            # Получаем file_id для данного фото
            photo_id = callback.message.photo[-1].file_id

            # Сохраняем file_id
            await state.update_data(photo_id=photo_id)

            # Редактируем photo_id для фотографии
            await callback.message.edit_caption(
                caption=LEXICON_RU['update_photo'],
                reply_markup=None
            )

            # Переходим в состояние FSM для редактирования photo_id
            await state.set_state(AdminUpdateDescriptionState.update_photo)
        else:
            await callback.answer(text=LEXICON_RU['buttons_not_active'])
            return
    except Exception as e:
        logger.error(f'Ошибка при обработке нажатия кнопки "Заменить сборку": {e}')
        await callback.answer(text=LEXICON_RU['error'])


@bot_admins_handlers_router.callback_query(F.data == 'update_description')
async def process_update_photo_description(callback: CallbackQuery,
                                           state: FSMContext,
                                           pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий на команду с кнопки "Изменить описание".
    :param callback: CallbackQuery от пользователя с параметрами для изменений описания.
    :param state: Состояние пользователя для FSM.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Проверяем, не вызвана ли команда /cancel
        data = await state.get_data()
        if not data.get('cancel_handler'):

            # Получаем file_id для данного фото
            photo_id = callback.message.photo[-1].file_id

            # Сохраняем file_id
            await state.update_data(photo_id=photo_id)

            # Если нет описания к фото
            if not callback.message.caption:
                raise Exception

            # Получаем описание к сборке из БД
            description = await get_photo_description_by_file_id_from_db(
                pool=pool,
                file_id=photo_id
            )

            # редактируем описание для фотографии
            await callback.message.edit_caption(
                caption=f'{LEXICON_RU["update_photo_description"]}'
                        f'{description}',
                reply_markup=None
            )
            # Переходим в состояние FSM для редактирования описания
            await state.set_state(AdminUpdateDescriptionState.update_description)
            # Обновляем данные в словаре data, добавляя в него file_id фотографии
            await state.update_data(photo_id=photo_id)
        else:
            await callback.answer(text=LEXICON_RU['buttons_not_active'])
            return
    except Exception as e:
        logger.error(f'Ошибка при обработке нажатия кнопки "Редактировать описание": {e}')
        await callback.answer(text=LEXICON_RU['error'])


@bot_admins_handlers_router.message(AdminUpdateDescriptionState.update_description)
async def update_photo_description_handler(message: Message,
                                           state: FSMContext):

    """
    Хендлер, срабатывающий на состояние в FSM для редактирования описания.
    :param message: Сообщение от пользователя.
    :param state: Состояние пользователя для FSM.
    :return: Функция ничего не возвращает.
    """

    try:
        # Создаём объект фильтра
        translit_filter = TransliterationFilter(mode='update')
        transliterated_text = await translit_filter(message)

        # Получаем словарь data из FSM
        data = await state.get_data()
        if not data:
            raise Exception

        # Получаем file_id фотографии
        photo_id = data.get('photo_id')

        # Обновляем данные в словаре data, добавляя в него новое описание для фотографии
        await state.update_data(new_description=transliterated_text.get('description'),
                                new_description_translit=transliterated_text.get('description_translit'))

        # Отправляем пользователю сообщение с новым описанием
        # и ждём подтверждения для обновления описания для фотографии
        await message.answer_photo(
            photo=photo_id,
            caption=f'{LEXICON_RU["new_photo_description"]}'
                    f'{message.text}\n'
                    f'{LEXICON_RU["confirm"]}',
            reply_markup=create_admins_confirmation_keyboard(command='update')
        )
    except Exception as e:
        logger.error(f'Ошибка при обработке добавлении нового описания в состояние для фото: {e}')
        await message.answer(text=LEXICON_RU['error'])


@bot_admins_handlers_router.callback_query(F.data.startswith('confirm_'))
async def process_confirm_callback(callback: CallbackQuery,
                                   state: FSMContext,
                                   pool: asyncpg.pool.Pool
                                   ):

    """
    Хендлер, срабатывающий на нажатие кнопок "Да" или "Нет"
    для добавления фото, удаления фото и изменения описания для фото.
    :param callback: CallbackQuery от пользователя с параметрами
    для подтверждения добавления, удаления или редактирования описания фотографии.
    :param state: Состояние пользователя для FSM.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    # Проверяем, не вызвана ли команда /cancel
    data = await state.get_data()
    if not data.get('cancel_handler'):
        # Получаем данные, какая команда (добавить, удалить, изменить) сейчас используется пользователем
        command = callback.data.split('_')[1]

        # Получаем Username пользователя
        user_name = callback.from_user.username
        # Получаем данные о file_id фотографии
        photo_id = data.get('photo_id')
        description_from_db = await get_photo_description_by_file_id_from_db(
            pool=pool,
            file_id=photo_id
        )

        # Обработка команды на добавление фото с описанием в БД
        if command == 'add':
            category = data.get('category')
            description = data.get('description')
            description_translit = data.get('description_translit')

            # Обработка нажатия кнопки "Да"
            if callback.data == 'confirm_add_yes':
                try:
                    # Добавляем фото с описанием в БД
                    await add_photo_with_category_to_db(
                        pool=pool,
                        photo_id=photo_id,
                        description=description,
                        description_translit=description_translit,
                        category_name=category
                    )
                    # Уведомляем пользователя об успешном выполнении операции
                    await callback.message.edit_text(text=LEXICON_RU['add_photo_confirm'])
                    # Очищаем состояние для дальнейшего его использования
                    await state.clear()
                except Exception as e:
                    logger.error(f'Ошибка при обработке запроса на добавление фото в БД: {e}')
                    await callback.message.edit_text(text=LEXICON_RU['error'])
            # Обработка нажатия кнопки "Нет"
            elif callback.data == 'confirm_add_no':
                # Уведомляем пользователя об отмене операции
                await callback.message.edit_text(text=LEXICON_RU['cancel'])
                # Очищаем состояние для дальнейшего его использования
                await state.clear()

        # Обработка команды на удаление фото из БД
        elif command == 'delete':
            # Обработка нажатия кнопки "да"
            if callback.data == 'confirm_delete_yes':
                try:
                    # Удаляем фото из БД
                    await delete_photo_from_db(
                        pool=pool,
                        photo_id=photo_id
                    )

                    # Удаляем фото из сообщения
                    await callback.message.delete()
                    logger.info(f'Фото {description_from_db} успешно удалено из БД администратором {user_name}.')
                    # Уведомляем пользователя об успешном удалении
                    await callback.message.answer(text=LEXICON_RU['delete_photo_successful'])
                    # Очищаем состояние для дальнейшего его использования
                    await state.clear()
                except Exception as e:
                    logger.error(f'Ошибка при обработке запроса на подтверждение удаления фото из БД: {e}')
                    await callback.message.manswer(text=LEXICON_RU['error'])
            # Обработка нажатия кнопки "Нет"
            elif callback.data == 'confirm_delete_no':
                # Возвращаем описание для фото
                await callback.message.edit_caption(
                    caption=f'{LEXICON_RU["photo_found"]} {description_from_db}'
                )
                # Очищаем состояние для дальнейшего его использования
                await state.clear()

        # Обработка команды на редактирование описания к фото
        elif command == 'update':
            # Получаем новое описание и категорию для фото
            new_description = data.get('new_description')
            new_description_translit = data.get('new_description_translit')
            # Обработка нажатия кнопки "Да"
            if callback.data == 'confirm_update_yes':
                try:
                    # Обновляем описание для фото в БД
                    await update_photo_description(
                        pool=pool,
                        photo_id=photo_id,
                        new_description=new_description,
                        new_description_translit=new_description_translit
                    )
                    logger.info(f'Описание для фото {description_from_db} успешно обновлено на {new_description} в БД '
                                f'администратором {user_name}.')
                    # Обновляем описание для фотографии в сообщении
                    await callback.message.edit_caption(
                        caption=f'{LEXICON_RU["new_photo_description"]}'
                                f'{new_description}'
                    )
                    # Очищаем состояние для дальнейшего его использования
                    await state.clear()
                except Exception as e:
                    logger.error(f'Ошибка при обработке запроса на подтверждение обновления описания фото в БД: {e}')
                    await callback.message.answer(text=LEXICON_RU['error'])
            # Обработка нажатия кнопки "Нет"
            elif callback.data == 'confirm_update_no':
                # Возвращаем старое описание для фото
                await callback.message.edit_caption(
                    caption=description_from_db
                )
                # Очищаем состояние для дальнейшего его использования
                await state.clear()

        # Обработка команды на замену фото
        elif command == 'replace':
            # Получаем новый photo_id, категорию и описание для фото
            new_photo_id = data.get('new_photo_id')
            # Обработка нажатия кнопки "Да"
            if callback.data == 'confirm_replace_yes':
                try:
                    # Заменяем фото в БД
                    await update_photo_in_db(pool=pool, photo_id=photo_id, new_photo_id=new_photo_id)
                    logger.info(f'photo_id у фото {description_from_db} успешно заменено на {new_photo_id} в БД '
                                f'администратором {user_name}.')
                    # Обновляем описание для фотографии в сообщении
                    await callback.message.edit_caption(caption=f'{LEXICON_RU["update_photo_successful"]}')
                    # Очищаем состояние для дальнейшего его использования
                    await state.clear()
                except Exception as e:
                    logger.error(f'Ошибка при обработке запроса на подтверждение замены фото в БД: {e}')
                    await callback.message.answer(text=LEXICON_RU['error'])
            # Обработка нажатия кнопки "Нет"
            elif callback.data == 'confirm_replace_no':
                # Удаляем фото из сообщения
                await callback.message.delete()
                # Возвращаем старое фото
                await callback.message.answer_photo(
                    photo=photo_id,
                    caption=f'{LEXICON_RU["update_photo_cancel"]}\n'
                )
                # Очищаем состояние для дальнейшего его использования
                await state.clear()

    else:
        await callback.answer(text=LEXICON_RU['buttons_not_active'])
        return

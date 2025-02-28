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
from bot_app.keyboards.keyboards import create_admins_confirmation_keyboard
from bot_app.lexicon.lexicon_common.lexicon_ru import LEXICON_RU
from bot_app.states.admin_states import AdminUpdateDescriptionState
from bot_app.utils.admin_check import check_is_admin

from config.database import (
    get_groups_from_db,
    get_categories_from_db,
    add_photo_with_category_to_db,
    delete_photo_from_db,
    update_photo_description,
    get_photo_description_by_file_id_from_db
)
from config.log import logger


# Создаём роутер для всех хендлеров, связанных с функциями администратора
bot_admins_handlers_router = Router(name='bot_admins_handlers_router')


@bot_admins_handlers_router.message(F.photo,
                                    TransliterationFilter)
async def check_message_for_photo(message: Message,
                                  dp: Dispatcher,
                                  pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий лишь на фотографию (в группах или ЛС администраторов групп)
    и описанием, которое начинается как одна из категорий.
    :param message: Сообщение от пользователя.
    :param dp: Объект Dispatcher.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Получаем категории, группы из БД
        categories = await get_categories_from_db(pool=pool)
        groups_id = await get_groups_from_db(pool=pool)

        # Получаем ID пользователя
        user_id = message.from_user.id

        # Проверяем, является ли пользователь администратором в одной из групп
        if not await check_is_admin(
                dp=dp,
                user_id=user_id,
                groups_id=groups_id
        ):
            await message.answer(text=LEXICON_RU['user_not_admin'])
            return

        # Разбиваем строку входящего сообщения на подстроки, если сообщение не пустое
        caption_split = message.caption.split(maxsplit=1) if message.caption else []

        # Проверяем длину сообщения, и, если больше одного слова и сообщение начинается с одной из категорий
        if len(caption_split) > 1 and caption_split[0] in categories:

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
async def process_delete_photo_callback(callback: CallbackQuery):

    """
    Хендлер, срабатывающий на команду с кнопки "Удалить сборку".
    :param callback: CallbackQuery от пользователя с параметром для удаления.
    :return: Функция ничего не возвращает.
    """

    try:
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
    except Exception as e:
        logger.error(f'Ошибка при обработке запроса на удаление фото: {e}')
        await callback.answer(text=LEXICON_RU['error'])


@bot_admins_handlers_router.callback_query(F.data == 'update_photo_description')
async def process_update_photo_description(callback: CallbackQuery,
                                           state: FSMContext):

    """
    Хендлер, срабатывающий на команду с кнопки "Изменить описание".
    :param callback: CallbackQuery от пользователя с параметрами для изменений описания.
    :param state: Состояние пользователя для FSM.
    :return: Функция ничего не возвращает.
    """

    try:
        # Если нет описания к фото
        if not callback.message.caption:
            raise Exception

        # редактируем описание для фотографии
        await callback.message.edit_caption(
            caption=LEXICON_RU['update_photo_description'],
            reply_markup=None
        )
        # Переходим в состояние FSM для редактирования описания
        await state.set_state(AdminUpdateDescriptionState.update_description)
        # Обновляем данные в словаре data, добавляя в него file_id фотографии
        await state.update_data(photo_id=callback.message.photo[0].file_id)
    except Exception as e:
        logger.error(f'Ошибка при обработке нажатия кнопки "Редактировать описание": {e}')
        await callback.answer(text=LEXICON_RU['error'])


@bot_admins_handlers_router.message(AdminUpdateDescriptionState.update_description,
                                    TransliterationFilter)
async def update_photo_description_handler(message: Message,
                                           state: FSMContext):

    """
    Хендлер, срабатывающий на состояние в FSM для редактирования описания.
    :param message: Сообщение от пользователя.
    :param state: Состояние пользователя для FSM.
    :return: Функция ничего не возвращает.
    """

    try:
        # Получаем словарь data из FSM
        data = await state.get_data()
        if not data:
            raise Exception

        # Получаем file_id фотографии
        photo_id = data.get('photo_id')

        # Преобразуем текст, если он на кириллице
        transformed_description = getattr(message, 'transliterated_text', message.text)

        # Обновляем данные в словаре data, добавляя в него новое описание для фотографии
        await state.update_data(new_description=transformed_description)

        # Отправляем пользователю сообщение с новым описанием
        # и ждём подтверждения для обновления описания для фотографии
        await message.answer_photo(
            photo=photo_id,
            caption=f'{LEXICON_RU["new_photo_description"]}'
                    f'{transformed_description}'
                    f'{LEXICON_RU["confirm"]}',
            reply_markup=create_admins_confirmation_keyboard(command='update')
        )
    except Exception as e:
        logger.error(f'Ошибка при обработке добавлении нового описания в состояние для фото: {e}')
        await message.answer(text=LEXICON_RU['error'])


@bot_admins_handlers_router.callback_query(F.data.startswith('confirm_'))
async def process_confirm_callback(callback: CallbackQuery,
                                   state: FSMContext,
                                   pool: asyncpg.pool.Pool):

    """
    Хендлер, срабатывающий на нажатие кнопок "Да" или "Нет"
    для добавления фото, удаления фото и изменения описания для фото
    :param callback: CallbackQuery от пользователя с параметрами
    для подтверждения добавления, удаления или редактирования описания фотографии
    :param state: Состояние пользователя для FSM.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    # Получаем данные, какая команда (добавить, удалить, изменить) сейчас используется пользователем
    command = callback.data.split('_')[1]
    # Получаем Username пользователя
    user_name = callback.from_user.username
    # Получаем данные о file_id фотографии и описания к ней
    photo_id = callback.message.photo[0].file_id
    description = await get_photo_description_by_file_id_from_db(
        pool=pool,
        file_id=photo_id
    )

    # Обработка команды на добавление фото с описанием в БД
    if command == 'add':
        # Разбиваем строку входящего сообщения на подстроки, если сообщение не пустое
        caption_split = callback.message.caption.split(maxsplit=1) if callback.message.caption else []
        # Обработка нажатия кнопки "Да"
        if callback.data == 'confirm_add_yes':
            try:
                # Преобразуем текст, если он на кириллице
                transformed_description = getattr(callback, 'transliterated_text', caption_split[1])
                # Добавляем фото с описанием в БД
                await add_photo_with_category_to_db(
                    pool=pool,
                    photo_id=photo_id,
                    description=transformed_description,
                    category_name=caption_split[0]
                )
                logger.info(f'Фото {caption_split[1]} успешно добавлено в БД '
                            f'администратором {user_name}.')
                # Уведомляем пользователя об успешном выполнении операции
                await callback.answer(text=LEXICON_RU['add_photo_confirm'])
                # Очищаем состояние для дальнейшего его использования
                await state.clear()
            except Exception as e:
                logger.error(f'Ошибка при обработке запроса на добавление фото в БД: {e}')
                await callback.answer(LEXICON_RU['error'])
        # Обработка нажатия кнопки "Нет"
        elif callback.data == 'confirm_add_no':
            # Уведомляем пользователя об отмене операции
            await callback.answer(LEXICON_RU['cancel'])
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
                logger.info(f'Фото {description} успешно удалено из БД администратором {user_name}.')
                # Уведомляем пользователя об успешном удалении
                await callback.answer(text=LEXICON_RU['delete_photo_successful'])
                # Очищаем состояние для дальнейшего его использования
                await state.clear()
            except Exception as e:
                logger.error(f'Ошибка при обработке запроса на подтверждение удаления фото из БД: {e}')
                await callback.answer(text=LEXICON_RU['error'])
        # Обработка нажатия кнопки "Нет"
        elif callback.data == 'confirm_delete_no':
            # Возвращаем описание для фото
            await callback.message.edit_caption(
                caption=f'{LEXICON_RU["photo_found"]} {description}'
            )
            # Очищаем состояние для дальнейшего его использования
            await state.clear()

    # Обработка команды на редактирование описания к фото
    elif command == 'update':
        # Получаем словарь data из FSM
        data = await state.get_data()
        # Получаем новое описание для фото
        new_description = data.get('new_description')
        # Обработка нажатия кнопки "Да"
        if callback.data == 'confirm_update_yes':
            try:
                # Обновляем описание для фото в БД
                await update_photo_description(
                    pool=pool,
                    photo_id=photo_id,
                    new_description=new_description
                )
                logger.info(f'Описание для фото {description} успешно обновлено на {new_description} в БД '
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
                await callback.answer(text=LEXICON_RU['error'])
        # Обработка нажатия кнопки "Нет"
        elif callback.data == 'confirm_update_no':
            # Возвращаем старое описание для фото
            await callback.message.edit_caption(
                caption=description
            )
            # Очищаем состояние для дальнейшего его использования
            await state.clear()

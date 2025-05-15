import json

import asyncpg

from config.config import DATABASE_URL
from config.log import logger

from bot_app.exceptions.database import (
    DatabaseConnectionError,
    DatabaseAddGroupError,
    DatabaseGetGroupError,
    DatabaseDeleteGroupError,
    DatabaseAddPhotoWithCategoryError,
    DatabaseGetPhotosError,
    DatabaseGetTotalPhotosError,
    DatabaseGetPhotoDescriptionByFileIdError,
    DatabaseGetFileIdByDescriptionError,
    DatabaseGetCategoriesError,
    DatabaseDeletePhotoError,
    DatabaseUpdatePhotoError,
    DatabaseUpdatePhotoDescriptionError,
    DatabaseSearchPhotoByDescriptionError
)
from bot_app.exceptions.photo import PhotoAlreadyExistsError


async def create_pool() -> asyncpg.pool.Pool:

    """
    Создание пула подключений к БД.
    :return: Возвращает объект пула подключения к БД.
    """

    try:
        # Возвращаем объект пула подключения к БД
        return await asyncpg.create_pool(dsn=DATABASE_URL)
    except Exception as e:
        raise DatabaseConnectionError.from_exception(e) from e


async def close_pool(pool: asyncpg.pool.Pool) -> None:

    """
    Закрытие пула подключений.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Закрываем пул соединения с БД
        await pool.close()
    except Exception as e:
        raise DatabaseConnectionError.from_exception(e) from e


async def add_group_to_db(pool: asyncpg.pool.Pool,
                          group_id: int,
                          group_name: str) -> None:

    """
    Добавление группы в таблицу групп.
    :param pool: Пул соединения с БД.
    :param group_id: ID группы из Telegram.
    :param group_name: Название группы из Telegram.
    :return: Функция ничего не возвращает.
    """

    try:
        # Запрос в БД из пула соединения
        async with pool.acquire() as conn:
            # Осуществляем добавление группы в БД
            await conn.execute(
                "INSERT INTO groups (group_id, group_name) "
                "VALUES ($1, $2) "
                "ON CONFLICT (group_id) DO NOTHING",
                group_id,
                group_name
            )
    except asyncpg.PostgresError as e:
        raise DatabaseAddGroupError(
            f'{type(e).__name__}: {e} | group_name: {group_name}, group_id: {group_id}'
        ) from e
    except Exception as e:
        raise DatabaseAddGroupError(
            f'{type(e).__name__}: {e} | group_name: {group_name}, group_id: {group_id}'
        ) from e


async def get_groups_from_db(pool: asyncpg.pool.Pool) -> list[int]:

    """
    Получение всех групп из БД.
    :param pool: Пул соединения с БД.
    :return: Возвращает список групп из БД.
    """

    try:
        # Возвращаем список групп
        async with pool.acquire() as conn:
            groups_id = await conn.fetchval(
                "SELECT ARRAY_AGG(group_id) "
                "FROM groups"
            )
            return groups_id if groups_id else []
    except asyncpg.PostgresError as e:
        raise DatabaseGetGroupError.from_exception(e) from e
    except Exception as e:
        raise DatabaseGetGroupError(f'Непредвиденная ошибка: {type(e).__name__}: {e}') from e


async def delete_group_from_db(pool: asyncpg.pool.Pool,
                               group_id: int) -> None:

    """
    Удаление группы из таблицы групп по ID.
    :param pool: Пул соединения с БД.
    :param group_id: ID группы из Telegram.
    :return: Функция ничего не возвращает.
    """

    try:
        # Удаляем группу из БД
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM groups "
                "WHERE group_id = $1",
                group_id
            )
    except asyncpg.exceptions.ForeignKeyViolationError as e:
        raise DatabaseDeleteGroupError(f'{type(e).__name__}: {e} | group_id: {group_id}') from e
    except Exception as e:
        raise DatabaseDeleteGroupError(f'{type(e).__name__}: {e} | group_id: {group_id}') from e


async def add_photo_with_category_to_db(pool: asyncpg.pool.Pool,
                                        photo_id: str,
                                        description: str,
                                        description_translit: str,
                                        category_name: str) -> None:

    """
    Добавление фото в таблицу photos и связь его с категорией в таблице categories.
    :param pool: Пул соединения с БД.
    :param photo_id: ID фотографии из Telegram.
    :param description: Описание фотографии.
    :param description_translit: Описание фотографии в переводе.
    :param category_name: Название категории, к которой относится фотография.
    :return: Функция ничего не возвращает.
    """

    try:
        # Добавление фото с категорией в БД
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Проверяем, есть ли фото с таким описанием в БД
                existing = await conn.fetchval(
                    "SELECT 1 "
                    "FROM photos "
                    "WHERE description = $1;",
                    description
                )
                if existing:
                    raise PhotoAlreadyExistsError(f'description: {description}')

                # Если категория уже была в БД, получаем её ID
                category_id = await conn.fetchval(
                    "SELECT id "
                    "FROM categories "
                    "WHERE category_name = $1;",
                    category_name
                )
                # Добавление категории, если её нет
                if category_id is None:
                    category_id = await conn.fetchval(
                        "INSERT INTO categories (category_name, category_description) " 
                        "VALUES ($1, $2) " 
                        "ON CONFLICT (category_name) "
                        "DO NOTHING "
                        "RETURNING id;",
                        category_name,
                        category_name
                    )
                    # Если всё ещё None — получаем ID вручную
                    if category_id is None:
                        category_id = await conn.fetchval(
                            "SELECT id "
                            "FROM categories "
                            "WHERE category_name = $1;",
                            category_name
                        )
                # Добавляем фото
                await conn.execute(
                    "INSERT INTO photos (photo_id, description, description_translit, category_id) "
                    "VALUES ($1, $2, $3, $4) "
                    "ON CONFLICT (photo_id) "
                    "DO UPDATE "
                    "SET "
                    "description = EXCLUDED.description, "
                    "description_translit = EXCLUDED.description_translit, "
                    "category_id = EXCLUDED.category_id ",
                    photo_id,
                    description,
                    description_translit,
                    category_id
                )

    except PhotoAlreadyExistsError:
        raise
    except asyncpg.PostgresError as e:
        raise DatabaseAddPhotoWithCategoryError.from_exception(e) from e
    except Exception as e:
        raise DatabaseAddPhotoWithCategoryError(
            f'{type(e).__name__}: {e} | description: {description}; category: {category_name}'
        ) from e


async def get_photos_from_db(pool: asyncpg.pool.Pool,
                             category: str,
                             limit: int,
                             offset: int) -> list[dict]:

    """
    Получение списка фотографий с пагинацией.
    :param pool: Пул соединений с БД.
    :param category: Категория из БД.
    :param limit: Параметр для ограничения в выводе фотографий.
    :param offset: Параметр для начала отсчёта ограничения.
    :return: Возвращает список словарей, содержащий в себе описание, file_id фотографии и id её в БД.
    """

    try:
        # Получаем список фотографий с описанием
        async with pool.acquire() as conn:
            # Получение category_id по названию категории
            category_row = await conn.fetchrow(
                "SELECT id "
                "FROM categories "
                "WHERE category_name = $1",
                category
            )
            if not category_row:
                logger.error(f'Категория "{category}" не найдена')
                return []

            category_id = category_row['id']

            # Получение фото по category_id
            rows = await conn.fetch(
                "SELECT id, photo_id, description "
                "FROM photos "
                "WHERE category_id = $1 "
                "ORDER BY id ASC "
                "LIMIT $2 "
                "OFFSET $3",
                category_id,
                limit,
                offset
            )

            photos = [dict(row) for row in rows]
            return photos
    except asyncpg.PostgresError as e:
        raise DatabaseGetPhotosError.from_exception(e) from e
    except Exception as e:
        raise DatabaseGetPhotosError.from_exception(e) from e


async def get_total_photos_count(pool: asyncpg.pool.Pool,
                                 category: str) -> int:

    """
    Получение общего числа фотографий для вычисления количества страниц.
    :param pool: Пул соединений с БД.
    :param category: Категория из БД.
    :return: Возвращает количество всех фотографий.
    """

    try:
        async with pool.acquire() as conn:
            # Получение category_id по названию категории
            category_row = await conn.fetchrow(
                "SELECT id "
                "FROM categories "
                "WHERE category_name = $1",
                category
            )

            category_id = category_row['id']
        # Получаем все фотографии по категории
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT COUNT(*) "
                "FROM photos "
                "WHERE category_id = $1",
                category_id
            )
            return result
    except asyncpg.PostgresError as e:
        raise DatabaseGetTotalPhotosError.from_exception(e) from e
    except Exception as e:
        raise DatabaseGetTotalPhotosError(f'{type(e).__name__}: {e} | category: {category}') from e


async def get_photo_description_by_file_id_from_db(pool: asyncpg.pool.Pool,
                                                   file_id: str) -> str:

    """
    Получение описания из БД для фотографии по её photo_id.
    :param pool: Пул соединения с БД.
    :param file_id: Ссылка на фотографию в Telegram.
    :return: Возвращает строку с описанием фотографии или Описания нет, пожалуйста, обратитесь к администратору.
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT description "
                "FROM photos "
                "WHERE photo_id = $1",
                file_id
            )
            if row:
                description = row['description']
                return description
            else:
                logger.warning(f'Описание не найдено по file_id={file_id}')
                return 'Описания нет, пожалуйста, обратитесь к администратору.'
    except asyncpg.PostgresError as e:
        raise DatabaseGetPhotoDescriptionByFileIdError(
            f'{type(e).__name__}: {e} | file_id: {file_id}'
        ) from e
    except Exception as e:
        raise DatabaseGetPhotoDescriptionByFileIdError(
            f'{type(e).__name__}: {e} | file_id: {file_id}'
        ) from e


async def get_photo_file_id_by_description_from_db(pool: asyncpg.pool.Pool,
                                                   description: str) -> str:

    """
    Получение file_id из БД для фотографии по её описанию.
    :param pool: Пул соединения с БД.
    :param description: Описание фотографии.
    :return: Возвращает строку с file_id фотографии или Описания нет, пожалуйста, обратитесь к администратору.
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT photo_id "
                "FROM photos "
                "WHERE description = $1",
                description
            )
            if row:
                file_id = row['photo_id']
                return file_id
            else:
                return 'file_id нет, пожалуйста, обратитесь к администратору.'
    except asyncpg.PostgresError as e:
        raise DatabaseGetFileIdByDescriptionError.from_exception(e) from e
    except Exception as e:
        raise DatabaseGetFileIdByDescriptionError(f'{type(e).__name__}: {e} | file_id: {file_id}') from e


async def get_categories_from_db(pool: asyncpg.pool.Pool) -> list[dict]:

    """
    Получение списка категорий.
    :param pool: Пул соединения с БД.
    :return: Возвращает список категорий.
    """

    try:
        async with pool.acquire() as conn:
            categories_json = await conn.fetchval(
                "SELECT JSON_AGG("
                "JSONB_BUILD_OBJECT('name', category_name, 'description', category_description) "
                "ORDER BY id ASC) "
                "FROM categories",
            )
            categories = json.loads(categories_json) if categories_json else []
            return categories
    except asyncpg.PostgresError as e:
        raise DatabaseGetCategoriesError.from_exception(e) from e
    except Exception as e:
        raise DatabaseGetCategoriesError(f'Неизвестная ошибка: {e}') from e


async def delete_photo_from_db(pool: asyncpg.pool.Pool,
                               photo_id: str) -> None:

    """
    Удаление фото по ID.
    :param pool: Пул соединений с БД
    :param photo_id: Айди фото для удаления его из БД
    :return: Функция ничего не возвращает
    """

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM photos "
                "WHERE photo_id = $1",
                photo_id
            )
            # Если фото не найдено
            if result == "DELETE 0":
                logger.warning(f'Фото с ID {photo_id} не найдено для удаления.')
    except asyncpg.exceptions.ForeignKeyViolationError as e:
        raise DatabaseDeletePhotoError(f'{type(e).__name__}: {e} | file_id: {photo_id}') from e
    except Exception as e:
        raise DatabaseDeletePhotoError(f'{type(e).__name__}: {e} | file_id: {photo_id}') from e


async def update_photo_in_db(pool: asyncpg.pool.Pool,
                             photo_id: str,
                             new_photo_id: str) -> None:

    """
    Обновление фото в БД.
    :param pool: Пул соединений с БД.
    :param photo_id: ID фотографии для обновления.
    :param new_photo_id: Новое ID фотографии.
    :return: Функция ничего не возвращает.
    """

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                'UPDATE photos '
                'SET photo_id = $1 '
                'WHERE photo_id = $2',
                new_photo_id,
                photo_id
            )
            # Если фото не найдено
            if result == 'UPDATE 0':
                logger.warning(f'Фото с ID {photo_id} не найдено в БД.')

    except asyncpg.PostgresError as e:
        raise DatabaseUpdatePhotoError(f'{type(e).__name__}: {e} | file_id: {photo_id}') from e
    except Exception as e:
        raise DatabaseUpdatePhotoError(
            f'{type(e).__name__}: {e} | file_id: {photo_id}, new_file_id: {new_photo_id}'
        ) from e


async def update_photo_description(pool: asyncpg.pool.Pool,
                                   photo_id: str,
                                   new_description: str,
                                   new_description_translit: str) -> None:

    """
    Обновление описания для фото в БД.
    :param pool: Пул соединений с БД.
    :param photo_id: ID фотографии для обновления.
    :param new_description: Новое описание для фотографии.
    :param new_description_translit: Новое описание для фотографии с переводом.
    :return: Функция ничего не возвращает.
    """

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                'UPDATE photos '
                'SET description = $1, '
                'description_translit = $2 '
                'WHERE photo_id = $3',
                new_description,
                new_description_translit,
                photo_id
            )
            # Если фото не найдено
            if result == 'UPDATE 0':
                logger.warning(f'Фото с ID {photo_id} не найдено в БД.')
    except asyncpg.PostgresError as e:
        raise DatabaseUpdatePhotoDescriptionError(f'{type(e).__name__}: {e} | file_id: {photo_id}') from e
    except Exception as e:
        raise DatabaseUpdatePhotoDescriptionError(
            f'{type(e).__name__}: {e} | file_id: {photo_id}, new_description: {new_description}'
        ) from e


async def search_photo_by_description_in_db(pool: asyncpg.pool.Pool,
                                            category: str,
                                            query: str) -> list[dict]:

    """
    Поиск фото по описанию в БД.
    :param pool: Пул соединений с БД.
    :param category: Категория для поиска.
    :param query: Поисковой запрос.
    :return: Возвращение списка словарей найденных записей.
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT description, description_translit, photo_id "
                "FROM photos "
                "JOIN categories "
                "ON photos.category_id = categories.id "
                "WHERE (description ILIKE $1 OR description_translit ILIKE $1) "
                "AND categories.category_name = $2 "
                "LIMIT 10",
                f'%{query}%',
                category
            )
        return [dict(row) for row in rows]
    except asyncpg.PostgresError as e:
        raise DatabaseSearchPhotoByDescriptionError.from_exception(e) from e
    except Exception as e:
        logger.error(f'Ошибка при поиске фото: {e}')
        return []

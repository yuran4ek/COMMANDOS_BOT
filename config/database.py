import asyncpg
from typing import List, Dict

from config.config import DATABASE_URL
from config.log import logger


async def create_pool() -> asyncpg.pool.Pool:

    """
    Создание пула подключений к БД.
    :return: Возвращает объект пула подключения к БД.
    """

    try:
        # Возвращаем объект пула подключения к БД
        return await asyncpg.create_pool(dsn=DATABASE_URL)
    except Exception as e:
        logger.error(f'Ошибка при создании пула подключений к БД: {e}')
        raise


async def close_pool(pool: asyncpg.pool.Pool) -> None:

    """
    Закрытие пула подключений.
    :param pool: Пул соединения с БД.
    :return: Функция ничего не возвращает.
    """

    try:
        # Закрываем пул соединения с БД
        await pool.close()
        logger.info('Успешное закрытие пула соединения с БД.')
    except Exception as e:
        logger.error(f'Ошибка при закрытии пула подключений: {e}')
        raise


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
            logger.info(f'Группа {group_name} с ID {group_id} была успешно добавлена в БД.')
    except asyncpg.exceptions.UniqueViolationError:
        logger.error(f'Группа {group_name} с ID {group_id} уже существует в базе данных.')
    except Exception as e:
        logger.error(f'Ошибка при добавлении группы в базу данных: {e}')
        raise


async def get_groups_from_db(pool: asyncpg.pool.Pool) -> List[int]:

    """
    Получение всех групп из БД.
    :param pool: Пул соединения с БД.
    :return: Возвращает список групп из БД.
    """

    try:
        # Возвращаем список групп
        async with pool.acquire() as conn:
            groups_id = await conn.fetch(
                "SELECT ARRAY_AGG(group_id) "
                "FROM groups"
            )
            logger.info(f'Группы были успешно получены из БД: {groups_id}')
            return groups_id or []
    except asyncpg.PostgresError as e:
        logger.error(f'Ошибка взаимодействия с базой данных при получении групп: {e}')
        raise
    except Exception as e:
        logger.error(f'Ошибка при получении групп: {e}')
        raise


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
        logger.info(f'Группа {group_id} успешно удалена из БД')
    except asyncpg.exceptions.ForeignKeyViolationError:
        logger.error(f'Невозможно удалить группу с ID {group_id}, так как она связана с другими данными')
    except Exception as e:
        logger.error(f'Ошибка при удалении группы из БД: {e}')
        raise


async def add_photo_with_category_to_db(pool: asyncpg.pool.Pool,
                                        photo_id: str,
                                        description: str,
                                        category_name: str) -> None:

    """
    Добавление фото в таблицу photos и связь его с категорией в таблице categories.
    :param pool: Пул соединения с БД.
    :param photo_id: ID фотографии из Telegram.
    :param description: Описание фотографии.
    :param category_name: Название категории, к которой относится фотография.
    :return: Функция ничего не возвращает.
    """

    try:
        # Добавление фото с категорией в БД
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Добавляем фото или получаем его ID
                photo_id_result = await conn.fetchval(
                    "INSERT INTO photos (photo_id, description) "
                    "VALUES ($1, $2) "
                    "ON CONFLICT (photo_id) "
                    "DO UPDATE "
                    "SET description = EXCLUDED.description "
                    "RETURNING id;",
                    photo_id,
                    description
                )

                # Добавляем категорию и связываем с фото
                await conn.execute(
                    "INSERT INTO categories (category_name, photo_id) "
                    "VALUES ($1, $2) "
                    "ON CONFLICT (category_name) DO UPDATE "
                    "SET photo_id = EXCLUDED.photo_id;",
                    category_name,
                    photo_id_result
                )

        logger.info(f'Фото "{description}" успешно добавлено в категорию "{category_name}"')

    except asyncpg.PostgresError as e:
        logger.error(f'Ошибка взаимодействия с базой данных: {e}')
    except Exception as e:
        logger.error(f'Произошла непредвиденная ошибка: {e}')


async def get_photos_from_db(pool: asyncpg.pool.Pool,
                             category: str,
                             limit: int,
                             offset: int) -> List[Dict]:

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
            rows = await conn.fetch(
                "SELECT photo_id, description "
                "FROM photos "
                "WHERE category = $1 "
                "LIMIT $2 "
                "OFFSET $3",
                category,
                limit,
                offset
            )
            photos = [dict(row) for row in rows]
            logger.info(f'Успешное получение фотографий: {photos}')
            return photos
    except asyncpg.PostgresError as e:
        logger.error(f'Ошибка взаимодействия с базой данных при получении фотографий: {e}')
        raise
    except Exception as e:
        logger.error(f'Ошибка при получении фотографий: {e}')
        raise


async def get_total_photos_count(pool: asyncpg.pool.Pool,
                                 category: str) -> int:

    """
    Получение общего числа фотографий для вычисления количества страниц.
    :param pool: Пул соединений с БД.
    :param category: Категория из БД.
    :return: Возвращает количество всех фотографий.
    """

    try:
        # Получаем все фотографии по категории
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT COUNT(*) "
                "FROM photos "
                "WHERE category = $1",
                category
            )
            logger.info(f'Успешное получение всех фотографий по категории {category}')
            return result
    except asyncpg.PostgresError as e:
        logger.error(f'Ошибка при получении количества фотографий: {e}')
        raise
    except Exception as e:
        logger.error(f'Ошибка при получении количества фотографий: {e}')
        raise


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
                logger.info(f'Успешное получение описания: "{description}"')
                return description
            else:
                return 'Описания нет, пожалуйста, обратитесь к администратору.'
    except asyncpg.PostgresError as e:
        logger.error(f'Ошибка при получении описания к фото: {e}')
        raise


async def get_categories_from_db(pool: asyncpg.pool.Pool) -> List[str]:

    """
    Получение списка категорий.
    :param pool: Пул соединения с БД.
    :return: Возвращает список категорий.
    """

    try:
        async with pool.acquire() as conn:
            category_name = await conn.fetch(
                "SELECT ARRAY_AGG(category_name) "
                "FROM categories",
            )
            logger.info(f'Категории были успешно получены из БД: {category_name}')
            return category_name or []
    except asyncpg.PostgresError as e:
        logger.error(f'Ошибка взаимодействия с базой данных при получении категорий: {e}')
        raise
    except Exception as e:
        logger.error(f'Ошибка при получении категорий: {e}')
        raise


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
    except asyncpg.exceptions.ForeignKeyViolationError:
        logger.error(f'Невозможно удалить фото с ID: {photo_id}, так как оно связано с другими данными')
    except Exception as e:
        logger.error(f'Ошибка при удалении фото из БД: {e}')
        raise


async def update_photo_description(pool: asyncpg.pool.Pool,
                                   photo_id: str,
                                   new_description: str) -> None:

    """
    Обновление описания для фото в БД.
    :param pool: Пул соединений с БД.
    :param photo_id: ID фотографии для обновления.
    :param new_description: новое описание для фотографии.
    :return: Функция ничего не возвращает.
    """

    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                'UPDATE photos SET description = $1 '
                'WHERE photo_id = $2',
                new_description,
                photo_id
            )
            # Если фото не найдено
            if result == 'UPDATE 0':
                logger.warning(f'Фото с ID {photo_id} не найдено в БД.')
            else:
                logger.info(f'Фото с ID {photo_id} успешно обновлено. Новое описание: {new_description}.')
    except asyncpg.PostgresError as e:
        logger.error(f'Ошибка при обновлении описания фото с ID {photo_id}: {e}')
        raise
    except Exception as e:
        logger.error(f'Ошибка при обновлении фото: {e}')


async def search_photo_by_description_in_db(pool: asyncpg.pool.Pool,
                                            query: str) -> List[Dict]:

    """
    Поиск фото по описанию в БД.
    :param pool: Пул соединений с БД
    :param query: Поисковой запрос
    :return: Возвращение списка словарей найденных записей.
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT description, category, photo_id '
                'FROM photos '
                'WHERE description ILIKE $1 '
                'LIMIT 10',
                f'%{query}%'
            )
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f'Ошибка при поиске фото: {e}')
        return []

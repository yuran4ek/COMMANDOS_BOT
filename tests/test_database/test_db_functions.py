import pytest

from unittest.mock import (
    patch,
    AsyncMock
)

from config.database import (
    create_pool,
    close_pool,
    add_group_to_db,
    get_groups_from_db,
    delete_group_from_db,
    add_photo_with_category_to_db,
    get_photos_from_db,
    get_total_photos_count,
    get_photo_description_by_file_id_from_db,
    get_categories_from_db,
    delete_photo_from_db,
    update_photo_description,
    search_photo_by_description_in_db
)


@pytest.mark.asyncio
@patch('config.database.DATABASE_URL', 'mock_dsn')
@patch('config.database.asyncpg.create_pool', new_callable=AsyncMock)
async def test_create_pool(mock_asyncpg_create_pool):

    """Тестирование успешного создания пула подключения."""

    mock_asyncpg_create_pool.return_value = 'mock_pool'

    pool = await create_pool()

    mock_asyncpg_create_pool.assert_called_once_with(dsn='mock_dsn')
    assert pool == 'mock_pool'


@pytest.mark.asyncio
@patch('config.database.close_pool', new_callable=AsyncMock)
async def test_close_pool(mock_pool):

    """Тестирование успешного закрытия пула подключения."""

    await close_pool(pool=mock_pool)
    mock_pool.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_group_to_db(mock_db_pool,
                               sample_test_data) -> None:

    """
    Тестирование функции добавления группы в базу данных.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    """

    group_data = sample_test_data['group']

    mock_pool, mock_conn = await mock_db_pool(data=group_data)

    group_id, group_name = group_data.values()

    await add_group_to_db(
        pool=mock_pool,
        group_id=group_id,
        group_name=group_name
    )

    mock_conn.execute.assert_called_once_with(
        "INSERT INTO groups (group_id, group_name) "
        "VALUES ($1, $2) "
        "ON CONFLICT (group_id) "
        "DO NOTHING",
        group_id,
        group_name
    )


@pytest.mark.asyncio
async def test_get_groups_from_db(mock_db_pool,
                                  sample_test_data) -> None:

    """
    Тестирование функции получения ID групп из БД.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    """

    groups = sample_test_data['groups']

    mock_pool, mock_conn = await mock_db_pool(data=groups)

    result = await get_groups_from_db(pool=mock_pool)

    mock_conn.fetch.assert_called_once_with(
        "SELECT ARRAY_AGG(group_id) "
        "FROM groups"
    )

    # Проверяем, что результат соответствует ожидаемому
    assert result == groups


@pytest.mark.asyncio
async def test_delete_group_from_db(mock_db_pool,
                                    sample_test_data) -> None:

    """
    Тестирование функции удаления группы из БД.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    """

    group = sample_test_data['group']

    mock_pool, mock_conn = await mock_db_pool(data=group)

    group_id = group['group_id']

    await delete_group_from_db(
        pool=mock_pool,
        group_id=group_id
    )

    mock_conn.execute.assert_called_once_with(
        "DELETE FROM groups "
        "WHERE group_id = $1",
        group_id
    )


@pytest.mark.asyncio
async def test_add_photo_with_category_to_db(mock_db_pool,
                                             sample_test_data) -> None:

    """
    Тестирование функции добавления фотографии с категорией в БД.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    """

    photo = sample_test_data['photo']

    photo_id, category, description, new_description = photo.values()

    mock_pool, mock_conn = await mock_db_pool(data=photo_id)

    await add_photo_with_category_to_db(
        pool=mock_pool,
        photo_id=photo_id,
        description=description,
        category_name=category
    )

    mock_conn.fetchval.assert_called_once_with(
        "INSERT INTO photos (photo_id, description) "
        "VALUES ($1, $2) "
        "ON CONFLICT (photo_id) "
        "DO UPDATE "
        "SET description = EXCLUDED.description "
        "RETURNING id;",
        photo_id,
        description
    )

    mock_conn.execute.assert_called_once_with(
        "INSERT INTO categories (category_name, photo_id) "
        "VALUES ($1, $2) "
        "ON CONFLICT (category_name) "
        "DO UPDATE "
        "SET photo_id = EXCLUDED.photo_id;",
        category,
        photo_id
    )


@pytest.mark.asyncio
async def test_get_photos_from_db(mock_db_pool,
                                  sample_test_data) -> None:

    """
    Тестирование функции получения фото из базы данных.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    """

    photo_data = sample_test_data['photos']

    category = next(iter({cat['category'] for cat in photo_data}))

    mock_pool, mock_conn = await mock_db_pool(data=photo_data)

    result = await get_photos_from_db(
        pool=mock_pool,
        category=category,
        limit=5,
        offset=0
    )

    mock_conn.fetch.assert_called_once_with(
        "SELECT photo_id, description "
        "FROM photos "
        "WHERE category = $1 "
        "LIMIT $2 "
        "OFFSET $3",
        category,
        5,
        0
    )

    assert result == photo_data


@pytest.mark.asyncio
async def test_get_total_photos_count(mock_db_pool,
                                      sample_test_data) -> None:

    """
    Тестирование функции получения всех фото из конкретной категории.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    """

    photo_data = sample_test_data['photos']

    category = next(iter({cat['category'] for cat in photo_data}))

    total_photos = len(photo_data)

    mock_pool, mock_conn = await mock_db_pool(data=total_photos)

    result = await get_total_photos_count(
        pool=mock_pool,
        category=category
    )

    mock_conn.fetchval.assert_called_once_with(
        "SELECT COUNT(*) "
        "FROM photos "
        "WHERE category = $1",
        category
    )

    assert result == total_photos


@pytest.mark.asyncio
async def test_get_photo_description_by_file_id_from_db(mock_db_pool,
                                                        sample_test_data) -> None:

    """
    Тестирование функции получения описания к фото по file_id из БД.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    """

    photo_data = sample_test_data['photo']

    photo_id = photo_data['photo_id']
    description = photo_data['description']

    mock_pool, mock_conn = await mock_db_pool(data=photo_data)

    result = await get_photo_description_by_file_id_from_db(
        pool=mock_pool,
        file_id=photo_id
    )

    mock_conn.fetchrow.assert_called_once_with(
        "SELECT description "
        "FROM photos "
        "WHERE photo_id = $1",
        photo_id
    )

    assert result == description


@pytest.mark.asyncio
async def test_get_categories_from_db(mock_db_pool,
                                      sample_test_data) -> None:

    """
    Тестирование функции получения категорий из БД.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    """

    category_data = sample_test_data['category']

    mock_poll, mock_conn = await mock_db_pool(data=category_data)

    result = await get_categories_from_db(pool=mock_poll)

    mock_conn.fetch.assert_called_once_with(
        "SELECT ARRAY_AGG(category_name) "
        "FROM categories"
    )

    assert result == category_data


@pytest.mark.asyncio
async def test_delete_photo_from_db(mock_db_pool,
                                    sample_test_data) -> None:

    """
    Тестирование функции удаления фото из БД.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    """

    photo_data = sample_test_data['photo']
    photo_id = photo_data['photo_id']

    mock_pool, mock_conn = await mock_db_pool(data=photo_data)

    await delete_photo_from_db(
        pool=mock_pool,
        photo_id=photo_id
    )

    mock_conn.execute.assert_called_once_with(
        "DELETE FROM photos "
        "WHERE photo_id = $1",
        photo_id
    )


@pytest.mark.asyncio
async def test_update_photo_description(mock_db_pool,
                                        sample_test_data) -> None:

    """
    Тестирование функции редактирования описания фото в БД.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    """

    photo_data = sample_test_data['photo']
    photo_id = photo_data['photo_id']
    new_description = photo_data['new_description']

    mock_pool, mock_conn = await mock_db_pool(data=photo_data)

    await update_photo_description(
        pool=mock_pool,
        photo_id=photo_id,
        new_description=new_description
    )

    mock_conn.execute.assert_called_once_with(
        "UPDATE photos "
        "SET description = $1 "
        "WHERE photo_id = $2",
        new_description,
        photo_id
    )


@pytest.mark.asyncio
async def test_search_photo_by_description_in_db(mock_db_pool,
                                                 sample_test_data) -> None:

    """
    Тестирование функции поиска фото по описанию в БД.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    """

    photo_data = sample_test_data['photos']
    query = '123'

    # Фильтруем данные, которые содержат '123' в description
    filtered_data = [
        photo for photo in photo_data if query in photo['description']
    ]

    mock_pool, mock_conn = await mock_db_pool(data=filtered_data)

    result = await search_photo_by_description_in_db(
        pool=mock_pool,
        query=query
    )

    mock_conn.fetch.assert_called_once_with(
        "SELECT description, category, photo_id "
        "FROM photos "
        "WHERE description ILIKE $1 "
        "LIMIT 10",
        f'%{query}%'
    )

    assert result == [photo_data[0]]

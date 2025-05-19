import pytest
import json
import asyncpg

from unittest.mock import (
    patch,
    call,
    AsyncMock
)
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
    get_photo_file_id_by_description_from_db,
    get_categories_from_db,
    delete_photo_from_db,
    update_photo_in_db,
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

    mock_asyncpg_create_pool.reset_mock()

    mock_asyncpg_create_pool.side_effect = TypeError('Type error')
    with pytest.raises(DatabaseConnectionError) as exc_info:
        await create_pool()

    assert 'TypeError' in str(exc_info.value)


@pytest.mark.asyncio
@patch('config.database.close_pool', new_callable=AsyncMock)
async def test_close_pool(mock_pool):

    """Тестирование успешного закрытия пула подключения."""

    await close_pool(pool=mock_pool)
    mock_pool.close.assert_awaited_once()

    mock_pool.close.reset_mock()

    mock_pool.close.side_effect = TypeError('Type error')
    with pytest.raises(DatabaseConnectionError) as exc_info:
        await close_pool(pool=mock_pool)

    assert 'TypeError' in str(exc_info.value)


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

    mock_conn.execute.reset_mock()

    mock_conn.execute.side_effect = asyncpg.PostgresError('DB error')
    with pytest.raises(DatabaseAddGroupError) as exc_info:
        await add_group_to_db(
            pool=mock_pool,
            group_id=group_id,
            group_name=group_name
        )

    assert 'DB error' in str(exc_info.value)

    mock_conn.execute.reset_mock()

    mock_conn.execute.side_effect = TypeError('Type error')
    with pytest.raises(DatabaseAddGroupError) as exc_info:
        await add_group_to_db(
            pool=mock_pool,
            group_id=group_id,
            group_name=group_name
        )

    assert 'Type error' in str(exc_info.value)


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

    mock_conn.fetchval.assert_called_once_with(
        "SELECT ARRAY_AGG(group_id) "
        "FROM groups"
    )

    # Проверяем, что результат соответствует ожидаемому
    assert result == groups

    mock_conn.fetchval.reset_mock()

    mock_conn.fetchval.side_effect = asyncpg.PostgresError('DB error')
    with pytest.raises(DatabaseGetGroupError) as exc_info:
        await get_groups_from_db(pool=mock_pool)

    assert 'DB error' in str(exc_info.value)

    mock_conn.execute.reset_mock()

    mock_conn.fetchval.side_effect = TypeError('Type error')
    with pytest.raises(DatabaseGetGroupError) as exc_info:
        await get_groups_from_db(pool=mock_pool)

    assert 'Type error' in str(exc_info.value)


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

    mock_conn.execute.reset_mock()

    mock_conn.execute.side_effect = asyncpg.exceptions.ForeignKeyViolationError('FK error')
    with pytest.raises(DatabaseDeleteGroupError) as exc_info:
        await delete_group_from_db(
            pool=mock_pool,
            group_id=group_id
        )

    assert 'FK error' in str(exc_info.value)

    mock_conn.execute.reset_mock()

    mock_conn.execute.side_effect = TypeError('Type error')
    with pytest.raises(DatabaseDeleteGroupError) as exc_info:
        await delete_group_from_db(
            pool=mock_pool,
            group_id=group_id
        )

    assert 'Type error' in str(exc_info.value)


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

    photo_id = photo["photo_id"]
    description = photo["description"]
    description_translit = photo["description_translit"]
    category = photo["category"]
    category_id = photo["category_id"]

    mock_pool, mock_conn = await mock_db_pool(data=photo)

    # Настраиваем fetchval через side_effect
    mock_conn.fetchval = AsyncMock(side_effect=[
        None,
        category_id,
        None
    ])

    await add_photo_with_category_to_db(
        pool=mock_pool,
        photo_id=photo_id,
        description=description,
        description_translit=description_translit,
        category_name=category
    )

    # Проверяем, что вызовы сделаны правильно
    mock_conn.fetchval.assert_has_calls([
        call(
            "SELECT 1 "
            "FROM photos "
            "WHERE description = $1;",
            description
        ),
        call(
            "SELECT id "
            "FROM categories "
            "WHERE category_name = $1;",
            category
        ),
    ], any_order=False)

    mock_conn.execute.assert_called_once_with(
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

    mock_conn.fetchval.reset_mock()
    mock_conn.execute.reset_mock()

    # Тестируем ошибку, чо фото уже есть
    mock_conn.fetchval.side_effect = lambda query, *args: (
        1 if "FROM photos "
             "WHERE description" in query else None
    )
    with pytest.raises(PhotoAlreadyExistsError):
        await add_photo_with_category_to_db(
            pool=mock_pool,
            photo_id=photo_id,
            description=description,
            description_translit=description_translit,
            category_name=category
        )

    mock_conn.fetchval.reset_mock()

    # Тестируем ошибку, связанную с БД
    mock_conn.fetchval.side_effect = asyncpg.PostgresError("DB error")
    with pytest.raises(DatabaseAddPhotoWithCategoryError) as exc_info:
        await add_photo_with_category_to_db(
            pool=mock_pool,
            photo_id=photo_id,
            description=description,
            description_translit=description_translit,
            category_name=category
        )
    assert "DB error" in str(exc_info.value)

    mock_conn.fetchval.reset_mock()

    # Тестируем неизвестную ошибку
    mock_conn.fetchval.side_effect = TypeError("Type error")
    with pytest.raises(DatabaseAddPhotoWithCategoryError) as exc_info:
        await add_photo_with_category_to_db(
            pool=mock_pool,
            photo_id=photo_id,
            description=description,
            description_translit=description_translit,
            category_name=category
        )
    assert "TypeError" in str(exc_info.value)


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
    category_id = sample_test_data['category_id']['id']

    mock_pool, mock_conn = await mock_db_pool(data={})

    mock_conn.fetchrow = AsyncMock(return_value={'id': category_id})
    mock_conn.fetch = AsyncMock(return_value=photo_data)

    result = await get_photos_from_db(
        pool=mock_pool,
        category=category,
        limit=5,
        offset=0
    )

    mock_conn.fetchrow.assert_called_once_with(
        "SELECT id "
        "FROM categories "
        "WHERE category_name = $1",
        category
    )

    mock_conn.fetch.assert_called_once_with(
        "SELECT id, photo_id, description "
        "FROM photos "
        "WHERE category_id = $1 "
        "ORDER BY id ASC "
        "LIMIT $2 "
        "OFFSET $3",
        category_id,
        5,
        0
    )

    assert result == photo_data

    mock_conn.fetchrow.reset_mock()
    mock_conn.fetch.reset_mock()

    # Тестируем ошибку, связанную с БД
    mock_conn.fetchrow.side_effect = asyncpg.PostgresError("DB error")
    with pytest.raises(DatabaseGetPhotosError) as exc_info:
        await get_photos_from_db(
            pool=mock_pool,
            category=category,
            limit=5,
            offset=0
        )
    assert "DB error" in str(exc_info.value)

    mock_conn.fetchrow.reset_mock()

    # Тестируем неизвестную ошибку
    mock_conn.fetchrow.side_effect = TypeError("Type error")
    with pytest.raises(DatabaseGetPhotosError) as exc_info:
        await get_photos_from_db(
            pool=mock_pool,
            category=category,
            limit=5,
            offset=0
        )
    assert "TypeError" in str(exc_info.value)


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
    category_id = sample_test_data['category_id']['id']

    total_photos = len(photo_data)

    mock_pool, mock_conn = await mock_db_pool(data={})

    mock_conn.fetchrow = AsyncMock(return_value={'id': category_id})
    mock_conn.fetchval = AsyncMock(return_value=total_photos)

    result = await get_total_photos_count(
        pool=mock_pool,
        category=category
    )

    mock_conn.fetchrow.assert_called_once_with(
        "SELECT id "
        "FROM categories "
        "WHERE category_name = $1",
        category
    )

    mock_conn.fetchval.assert_called_once_with(
        "SELECT COUNT(*) "
        "FROM photos "
        "WHERE category_id = $1",
        category_id
    )

    assert result == total_photos

    mock_conn.fetchrow.reset_mock()
    mock_conn.fetchval.reset_mock()

    # Тестируем ошибку, связанную с БД
    mock_conn.fetchrow.side_effect = asyncpg.PostgresError("DB error")
    with pytest.raises(DatabaseGetTotalPhotosError) as exc_info:
        await get_total_photos_count(
            pool=mock_pool,
            category=category
        )
    assert "DB error" in str(exc_info.value)

    mock_conn.fetchrow.reset_mock()

    # Тестируем неизвестную ошибку
    mock_conn.fetchrow.side_effect = TypeError("Type error")
    with pytest.raises(DatabaseGetTotalPhotosError) as exc_info:
        await get_total_photos_count(
            pool=mock_pool,
            category=category
        )
    assert "TypeError" in str(exc_info.value)


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

    mock_conn.fetchrow.reset_mock()

    # Тестируем ошибку, связанную с БД
    mock_conn.fetchrow.side_effect = asyncpg.PostgresError("DB error")
    with pytest.raises(DatabaseGetPhotoDescriptionByFileIdError) as exc_info:
        await get_photo_description_by_file_id_from_db(
            pool=mock_pool,
            file_id=photo_id
        )
    assert "DB error" in str(exc_info.value)

    mock_conn.fetchrow.reset_mock()

    # Тестируем неизвестную ошибку
    mock_conn.fetchrow.side_effect = TypeError("Type error")
    with pytest.raises(DatabaseGetPhotoDescriptionByFileIdError) as exc_info:
        await get_photo_description_by_file_id_from_db(
            pool=mock_pool,
            file_id=photo_id
        )
    assert "TypeError" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_photo_file_id_by_description_from_db(mock_db_pool,
                                                        sample_test_data) -> None:

    """
    Тестирование функции получения file_id фото по его описанию из БД.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    :return:
    """

    photo_data = sample_test_data['photo']

    photo_id = photo_data['photo_id']
    description = photo_data['description']

    mock_pool, mock_conn = await mock_db_pool(data=photo_data)

    result = await get_photo_file_id_by_description_from_db(
        pool=mock_pool,
        description=description
    )

    mock_conn.fetchrow.assert_called_once_with(
        "SELECT photo_id "
        "FROM photos "
        "WHERE description = $1",
        description
    )

    assert result == photo_id

    mock_conn.fetchrow.reset_mock()

    # Тестируем ошибку, связанную с БД
    mock_conn.fetchrow.side_effect = asyncpg.PostgresError("DB error")
    with pytest.raises(DatabaseGetFileIdByDescriptionError) as exc_info:
        await get_photo_file_id_by_description_from_db(
            pool=mock_pool,
            description=description
        )
    assert "DB error" in str(exc_info.value)

    mock_conn.fetchrow.reset_mock()

    # Тестируем неизвестную ошибку
    mock_conn.fetchrow.side_effect = TypeError("Type error")
    with pytest.raises(DatabaseGetFileIdByDescriptionError) as exc_info:
        await get_photo_file_id_by_description_from_db(
            pool=mock_pool,
            description=description
        )
    assert "TypeError" in str(exc_info.value)


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
    category_json = json.dumps(category_data)

    mock_poll, mock_conn = await mock_db_pool(data=category_json)

    result = await get_categories_from_db(pool=mock_poll)

    mock_conn.fetchval.assert_called_once_with(
        "SELECT JSON_AGG("
        "JSONB_BUILD_OBJECT('name', category_name, 'description', category_description) "
        "ORDER BY id ASC) "
        "FROM categories"
    )

    assert result == category_data

    mock_conn.fetchval.reset_mock()

    # Тестируем ошибку, связанную с БД
    mock_conn.fetchval.side_effect = asyncpg.PostgresError("DB error")
    with pytest.raises(DatabaseGetCategoriesError) as exc_info:
        await get_categories_from_db(pool=mock_poll)
    assert "DB error" in str(exc_info.value)

    mock_conn.fetchval.reset_mock()

    # Тестируем неизвестную ошибку
    mock_conn.fetchval.side_effect = TypeError("Type error")
    with pytest.raises(DatabaseGetCategoriesError) as exc_info:
        await get_categories_from_db(pool=mock_poll)
    assert "TypeError" in str(exc_info.value)


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

    mock_conn.execute.reset_mock()

    # Тестируем ошибку, связанную с БД
    mock_conn.execute.side_effect = asyncpg.PostgresError("DB error")
    with pytest.raises(DatabaseDeletePhotoError) as exc_info:
        await delete_photo_from_db(
            pool=mock_pool,
            photo_id=photo_id
        )
    assert "DB error" in str(exc_info.value)

    mock_conn.execute.reset_mock()

    # Тестируем неизвестную ошибку
    mock_conn.execute.side_effect = TypeError("Type error")
    with pytest.raises(DatabaseDeletePhotoError) as exc_info:
        await delete_photo_from_db(
            pool=mock_pool,
            photo_id=photo_id
        )
    assert "TypeError" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_photo_in_db(mock_db_pool,
                                  sample_test_data) -> None:

    """
    Тестирование функции редактирования фото в БД.
    :param mock_db_pool: Функция, которая принимает данные и возвращает корутину,
    возвращающая кортеж из мокированного пула соединений и само соединение с БД.
    :param sample_test_data: Словарь с тестовыми данными.
    :return: Функция ничего не возвращает.
    """

    photo_data = sample_test_data['photo']
    photo_id = photo_data['photo_id']
    new_photo_id = 'photo321'

    mock_pool, mock_conn = await mock_db_pool(data=photo_data)

    await update_photo_in_db(
        pool=mock_pool,
        photo_id=photo_id,
        new_photo_id=new_photo_id
    )

    mock_conn.execute.assert_called_once_with(
        "UPDATE photos "
        "SET photo_id = $1 "
        "WHERE photo_id = $2",
        new_photo_id,
        photo_id
    )

    mock_conn.execute.reset_mock()

    # Тестируем ошибку, связанную с БД
    mock_conn.execute.side_effect = asyncpg.PostgresError("DB error")
    with pytest.raises(DatabaseUpdatePhotoError) as exc_info:
        await update_photo_in_db(
            pool=mock_pool,
            photo_id=photo_id,
            new_photo_id=new_photo_id
        )
    assert "DB error" in str(exc_info.value)

    mock_conn.execute.reset_mock()

    # Тестируем неизвестную ошибку
    mock_conn.execute.side_effect = TypeError("Type error")
    with pytest.raises(DatabaseUpdatePhotoError) as exc_info:
        await update_photo_in_db(
            pool=mock_pool,
            photo_id=photo_id,
            new_photo_id=new_photo_id
        )
    assert "TypeError" in str(exc_info.value)


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
    new_description_translit = photo_data['new_description_translit']

    mock_pool, mock_conn = await mock_db_pool(data=photo_data)

    await update_photo_description(
        pool=mock_pool,
        photo_id=photo_id,
        new_description=new_description,
        new_description_translit=new_description_translit
    )

    mock_conn.execute.assert_called_once_with(
        "UPDATE photos "
        "SET description = $1, "
        "description_translit = $2 "
        "WHERE photo_id = $3",
        new_description,
        new_description_translit,
        photo_id
    )

    mock_conn.execute.reset_mock()

    # Тестируем ошибку, связанную с БД
    mock_conn.execute.side_effect = asyncpg.PostgresError("DB error")
    with pytest.raises(DatabaseUpdatePhotoDescriptionError) as exc_info:
        await update_photo_description(
            pool=mock_pool,
            photo_id=photo_id,
            new_description=new_description,
            new_description_translit=new_description_translit
        )
    assert "DB error" in str(exc_info.value)

    mock_conn.execute.reset_mock()

    # Тестируем неизвестную ошибку
    mock_conn.execute.side_effect = TypeError("Type error")
    with pytest.raises(DatabaseUpdatePhotoDescriptionError) as exc_info:
        await update_photo_description(
            pool=mock_pool,
            photo_id=photo_id,
            new_description=new_description,
            new_description_translit=new_description_translit
        )
    assert "TypeError" in str(exc_info.value)


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
    category = next(iter({cat['category'] for cat in photo_data}))
    query = '123'

    # Фильтруем данные, которые содержат '123' в description
    filtered_data = [
        photo for photo in photo_data if query in photo['description']
    ]

    mock_pool, mock_conn = await mock_db_pool(data=filtered_data)

    result = await search_photo_by_description_in_db(
        pool=mock_pool,
        category=category,
        query=query
    )

    mock_conn.fetch.assert_called_once_with(
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

    assert result == [photo_data[0]]

    mock_conn.fetch.reset_mock()

    # Тестируем ошибку, связанную с БД
    mock_conn.fetch.side_effect = asyncpg.PostgresError("DB error")
    with pytest.raises(DatabaseSearchPhotoByDescriptionError) as exc_info:
        await search_photo_by_description_in_db(
            pool=mock_pool,
            category=category,
            query=query
        )
    assert "DB error" in str(exc_info.value)

    mock_conn.fetch.reset_mock()

    # Тестируем неизвестную ошибку
    mock_conn.fetch.side_effect = TypeError("Type error")
    with pytest.raises(DatabaseSearchPhotoByDescriptionError) as exc_info:
        await search_photo_by_description_in_db(
            pool=mock_pool,
            category=category,
            query=None
        )
    assert "Type error" in str(exc_info.value)

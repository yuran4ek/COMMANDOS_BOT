import os
import logging
from logging.handlers import RotatingFileHandler


# Определяем корневую директорию проекта
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Путь к директории логов
log_dir = os.path.join(BASE_DIR, 'logs')
log_file = os.path.join(log_dir, 'bot.log')

# Создание папки logs
os.makedirs(log_dir, exist_ok=True)

# Обработчик для ротации логов (5 файлов по 1 MB каждый)
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)

# Формат логов
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
file_handler.setFormatter(formatter)

# Настройка логирования
logging.basicConfig(
    # Уровень логов: DEBUG, INFO, WARNING, ERROR, CRITICAL
    level=logging.INFO,
    handlers=[file_handler],
    force=True
)

# Логгер для использования в проекте
logger = logging.getLogger("bot")

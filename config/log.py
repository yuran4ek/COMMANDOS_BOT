import os
import logging
from logging.handlers import RotatingFileHandler


# Путь к директории логов
log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
log_file = os.path.join(log_dir, 'bot_log')

# Создание папки logs
os.makedirs(log_dir, exist_ok=True)

# Обработчик для ротации логов (5 файлов по 1 MB каждый)
file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)

# Формат логов
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
file_handler.setFormatter(formatter)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Уровень логов: DEBUG, INFO, WARNING, ERROR, CRITICAL
    handlers=[file_handler],
)

# Логгер для использования в проекте
logger = logging.getLogger("bot")

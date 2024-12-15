import logging
from logging.handlers import RotatingFileHandler


# Настройка ротации логов
log_file = "logs/bot.log"

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

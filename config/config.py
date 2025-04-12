from dotenv import load_dotenv
import os


# Подключаем библиотеку для хранения персональных данных
load_dotenv()


# Токен бота из Telegram
BOT_TOKEN = os.getenv('BOT_TOKEN')
# Путь к БД
DATABASE_URL = os.getenv('DATABASE_URL')

# URL для отправки команды /start в ссылке на бота
BOT_URL_FOR_START = os.getenv('BOT_URL_FOR_START')

# URL для перехода в канал COMMANDOS
CHANEL_URL = os.getenv('CHANEL_URL')

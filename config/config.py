from dotenv import load_dotenv
import os


load_dotenv()


BOT_TOKEN = os.getenv('BOT_TOKEN')
GROUP_PUBLICATION_CHAT_ID = os.getenv('GROUP_PUBLICATION_CHAT_ID')
GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID')
DATABASE_URL = os.getenv('DATABASE_URL')

# Конфигурация бота
import os

# Токен бота берётся из локальной переменной окружения API_TOKEN
API_TOKEN = os.getenv("API_TOKEN", "").strip()

# ID главного администратора (получить у @userinfobot)
MAIN_ADMIN_ID = 5861625780  # Замени на свой ID

# Путь к папке с данными и базе данных
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "bot.db")

# Конфигурация бота
BOT_TOKEN = "8328797195:AAHFETTsxmK_JChPVfVI7u6TFExAxFqpl1Y"  # Получить у @BotFather

# ID главного администратора (получить у @userinfobot)
MAIN_ADMIN_ID = 5861625780  # Замени на свой ID

# Путь к папке с данными и базе данных
import os
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "bot.db")

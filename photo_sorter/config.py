import os
import sys

# Базовый каталог приложения (рядом с исполняемым файлом или в AppData)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Папки для сортировки
UNSORTED_DIR = os.path.join(BASE_DIR, "unsorted")
SORTED_CHILD = os.path.join(BASE_DIR, "sorted", "child")
SORTED_DOUBTFUL = os.path.join(BASE_DIR, "sorted", "doubtful")
SORTED_ADULT = os.path.join(BASE_DIR, "sorted", "adult")

# База данных SQLite
DATABASE_PATH = os.path.join(BASE_DIR, "sorter.db")

# Поддерживаемые расширения изображений
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}

def create_directories():
    """Создаёт все необходимые папки, если их нет."""
    for dir_path in (UNSORTED_DIR, SORTED_CHILD, SORTED_DOUBTFUL, SORTED_ADULT):
        os.makedirs(dir_path, exist_ok=True)
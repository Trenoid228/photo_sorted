import os
import shutil
from config import IMAGE_EXTENSIONS

class FileOperations:
    @staticmethod
    def ensure_dir(directory):
        """Создаёт директорию, если её нет (включая промежуточные)."""
        os.makedirs(directory, exist_ok=True)

    @staticmethod
    def move_file(src, dst):
        """Перемещает файл, создавая целевую папку при необходимости."""
        FileOperations.ensure_dir(os.path.dirname(dst))
        shutil.move(src, dst)

    @staticmethod
    def is_image(file_path):
        """Проверяет, является ли файл изображением по расширению."""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in IMAGE_EXTENSIONS

    @staticmethod
    def get_image_files(directory):
        """Возвращает список путей всех файлов изображений в каталоге (рекурсивно)."""
        image_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                full_path = os.path.join(root, file)
                if FileOperations.is_image(full_path):
                    image_files.append(full_path)
        return image_files
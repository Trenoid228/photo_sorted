import os
from database.db_manager import DatabaseManager
from file_manager.file_operations import FileOperations
from config import SORTED_CHILD, SORTED_DOUBTFUL, SORTED_ADULT

class PhotoSorter:
    """
    Контроллер сортировки. Предоставляет методы для получения следующего неотсортированного
    изображения и перемещения его в целевую папку с обновлением статуса в БД.
    """
    def __init__(self):
        self.db = DatabaseManager()
        self.category_dirs = {
            'child': SORTED_CHILD,
            'doubtful': SORTED_DOUBTFUL,
            'adult': SORTED_ADULT
        }
        # Убедимся, что целевые папки существуют
        for path in self.category_dirs.values():
            FileOperations.ensure_dir(path)

    def get_next_unsorted(self):
        """
        Возвращает кортеж (id, current_path) или None, если очередь пуста.
        """
        return self.db.get_next_unsorted()

    def sort_photo(self, photo_id: int, category: str) -> bool:
        """
        Перемещает фото в папку категории и обновляет БД.
        Возвращает True в случае успеха.
        """
        if category not in self.category_dirs:
            return False

        photo = self.db.get_photo_by_id(photo_id)
        if not photo:
            return False

        current_path = photo[1]
        dest_dir = self.category_dirs[category]
        filename = os.path.basename(current_path)
        dest_path = os.path.join(dest_dir, filename)

        # Генерация уникального имени, если файл уже существует в целевой папке
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while True:
                new_name = f"{base}_{counter}{ext}"
                dest_path = os.path.join(dest_dir, new_name)
                if not os.path.exists(dest_path):
                    break
                counter += 1

        try:
            FileOperations.move_file(current_path, dest_path)
            self.db.update_status(photo_id, category, dest_path)
            return True
        except Exception as e:
            print(f"Error sorting photo {photo_id}: {e}")
            return False

    @property
    def unsorted_count(self):
        return self.db.count_unsorted()
import os
from downloader.base_downloader import BaseDownloader
from file_manager.archive_handler import ArchiveHandler, ZipExtractor
from file_manager.file_operations import FileOperations
from database.db_manager import DatabaseManager

class LocalArchiveDownloader(BaseDownloader):
    def __init__(self, archive_handler: ArchiveHandler = None):
        """
        :param archive_handler: реализация ArchiveHandler (по умолчанию ZipExtractor)
        """
        self.archive_handler = archive_handler or ZipExtractor()

    def download(self, source: str, dest_dir: str) -> list:
        """
        1. Распаковывает архив во временную папку внутри dest_dir.
        2. Отбирает только файлы изображений.
        3. Переносит каждое изображение в dest_dir (если его там ещё нет).
        4. Регистрирует файл в базе данных, если он ещё не известен.
        Возвращает список путей к файлам в dest_dir, успешно добавленным как unsorted.
        """
        temp_extract = os.path.join(dest_dir, "_temp_extract")
        extracted = self.archive_handler.extract(source, temp_extract)
        # Извлечённые файлы: отбираем изображения
        image_files = [f for f in extracted if FileOperations.is_image(f) and os.path.isfile(f)]

        db = DatabaseManager()
        result_files = []

        for img_path in image_files:
            # Имя файла
            filename = os.path.basename(img_path)
            dest_path = os.path.join(dest_dir, filename)

            # Если файл с таким именем уже существует в unsorted, генерируем уникальное имя
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while True:
                    new_name = f"{base}_{counter}{ext}"
                    dest_path = os.path.join(dest_dir, new_name)
                    if not os.path.exists(dest_path):
                        break
                    counter += 1

            # Перемещаем файл в целевую папку unsorted
            FileOperations.move_file(img_path, dest_path)

            # Регистрируем в БД (original_path = исходный путь в архиве? лучше сохранить source архива)
            # Но чтобы избежать дублирования по содержимому, проверяем по original_path (путь внутри архива)
            # Однако после перемещения original_path может быть неактуален.
            # Лучше хранить хеш файла? Пока для простоты используем dest_path как original_path и current_path.
            # Проверяем, не добавлен ли уже файл с таким dest_path (или original_path)
            if not db.is_known_file(dest_path):  # используем dest_path как идентификатор
                db.add_photo(original_path=dest_path, current_path=dest_path)
                result_files.append(dest_path)

        # Удаляем временную папку распаковки
        FileOperations.ensure_dir(dest_dir)  # на всякий случай
        import shutil
        shutil.rmtree(temp_extract, ignore_errors=True)

        return result_files
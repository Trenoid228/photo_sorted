import zipfile
import os
from abc import ABC, abstractmethod

class ArchiveHandler(ABC):
    """Интерфейс для извлечения архивов (Strategy)."""
    @abstractmethod
    def extract(self, archive_path: str, destination: str) -> list:
        """Извлекает архив в destination и возвращает список путей извлечённых файлов."""
        pass

class ZipExtractor(ArchiveHandler):
    def extract(self, archive_path: str, destination: str) -> list:
        os.makedirs(destination, exist_ok=True)
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(destination)
            # namelist() содержит полные пути относительно корня архива
            extracted_files = [os.path.join(destination, f) for f in zip_ref.namelist()]
        return extracted_files
from abc import ABC, abstractmethod

class BaseDownloader(ABC):
    """Абстрактный загрузчик/импортёр."""
    @abstractmethod
    def download(self, source: str, dest_dir: str) -> list:
        """
        Выполняет импорт из source в dest_dir.
        Возвращает список путей к итоговым файлам, готовым к добавлению в unsorted.
        """
        pass
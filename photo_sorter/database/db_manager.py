import sqlite3
import os
import threading
from config import DATABASE_PATH

class DatabaseManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL;")  # для конкурентного доступа
        self._init_db()

    def _init_db(self):
        cursor = self.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT NOT NULL,
                current_path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unsorted',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sorted_at TIMESTAMP
            )
        ''')
        self.connection.commit()

    def add_photo(self, original_path, current_path):
        """Добавляет фото в базу со статусом 'unsorted'."""
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO photos (original_path, current_path, status) VALUES (?, ?, 'unsorted')",
            (original_path, current_path)
        )
        self.connection.commit()
        return cursor.lastrowid
    
    def get_photo_by_id(self, photo_id):
        """Возвращает (id, current_path) для заданного id или None."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT id, current_path FROM photos WHERE id = ?", (photo_id,))
        return cursor.fetchone()

    def get_next_unsorted(self):
        """Возвращает (id, current_path) первого неотсортированного фото или None."""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT id, current_path FROM photos WHERE status = 'unsorted' ORDER BY id LIMIT 1"
        )
        return cursor.fetchone()

    def update_status(self, photo_id, new_status, new_path):
        """Обновляет статус и путь файла после перемещения."""
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE photos SET status = ?, current_path = ?, sorted_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_status, new_path, photo_id)
        )
        self.connection.commit()

    def is_known_file(self, original_path):
        """Проверяет, есть ли уже запись с таким original_path."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM photos WHERE original_path = ?", (original_path,))
        return cursor.fetchone()[0] > 0

    def count_unsorted(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM photos WHERE status = 'unsorted'")
        return cursor.fetchone()[0]

    def close(self):
        if self.connection:
            self.connection.close()
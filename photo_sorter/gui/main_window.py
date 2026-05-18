import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox,
    QStatusBar
)
from PyQt5.QtCore import Qt

from gui.image_widget import ImageWidget
from downloader.local_archive import LocalArchiveDownloader
from sorter.sorter import PhotoSorter
from config import UNSORTED_DIR


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Сортировщик фотографий")
        self.setGeometry(100, 100, 900, 700)

        # Создаём экземпляры контроллеров
        self.sorter = PhotoSorter()
        self.downloader = LocalArchiveDownloader()

        # Текущее отображаемое фото (id, path)
        self.current_photo = None

        # Инициализация интерфейса
        self._init_ui()

        # Проверяем, есть ли уже неотсортированные фотографии
        self._refresh_state()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Верхняя панель с кнопкой импорта
        top_layout = QHBoxLayout()
        self.import_btn = QPushButton("📥 Импортировать архив")
        self.import_btn.clicked.connect(self._on_import_archive)
        top_layout.addWidget(self.import_btn)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # Область отображения фото
        self.image_widget = ImageWidget()
        main_layout.addWidget(self.image_widget, stretch=1)

        # Информация о файле
        self.file_info_label = QLabel("Файл не выбран")
        self.file_info_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.file_info_label)

        # Панель кнопок категорий
        categories_layout = QHBoxLayout()
        self.child_btn = QPushButton("👶 Ребёнок")
        self.doubtful_btn = QPushButton("❓ Сомнительно")
        self.adult_btn = QPushButton("🧑 Взрослый")

        for btn in (self.child_btn, self.doubtful_btn, self.adult_btn):
            btn.setMinimumHeight(50)
            btn.setEnabled(False)
            categories_layout.addWidget(btn)

        self.child_btn.clicked.connect(lambda: self._on_category('child'))
        self.doubtful_btn.clicked.connect(lambda: self._on_category('doubtful'))
        self.adult_btn.clicked.connect(lambda: self._on_category('adult'))

        main_layout.addLayout(categories_layout)

        # Статусная строка
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status_message()

    def _on_import_archive(self):
        """Диалог выбора архива, распаковка в UNSORTED_DIR."""
        archive_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите архив", "",
            "ZIP архивы (*.zip);;Все файлы (*)"
        )
        if not archive_path:
            return

        try:
            added_files = self.downloader.download(archive_path, UNSORTED_DIR)
            QMessageBox.information(
                self, "Импорт завершён",
                f"Добавлено новых фотографий: {len(added_files)}"
            )
            self._refresh_state()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))

    def _on_category(self, category):
        """Обработка нажатия кнопки категории."""
        if not self.current_photo:
            return

        photo_id = self.current_photo[0]
        success = self.sorter.sort_photo(photo_id, category)
        if not success:
            QMessageBox.warning(self, "Ошибка", "Не удалось переместить файл.")

        self._refresh_state()

    def _refresh_state(self):
        """Обновляет GUI в зависимости от наличия неотсортированных фото."""
        self.current_photo = self.sorter.get_next_unsorted()

        if self.current_photo:
            photo_id, path = self.current_photo
            self.image_widget.set_image(path)
            self.file_info_label.setText(os.path.basename(path))
            # Активируем кнопки категорий
            self.child_btn.setEnabled(True)
            self.doubtful_btn.setEnabled(True)
            self.adult_btn.setEnabled(True)
        else:
            self.image_widget.clear_image()
            self.file_info_label.setText("Все фотографии отсортированы")
            self.child_btn.setEnabled(False)
            self.doubtful_btn.setEnabled(False)
            self.adult_btn.setEnabled(False)

        self._update_status_message()

    def _update_status_message(self):
        unsorted = self.sorter.unsorted_count
        self.status_bar.showMessage(f"Осталось неотсортированных: {unsorted}")
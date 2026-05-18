from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

class ImageWidget(QLabel):
    """Виджет для отображения изображения с сохранением пропорций при изменении размера."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        self._pixmap = None

    def set_image(self, image_path):
        """Загружает изображение и масштабирует под текущий размер виджета."""
        self._pixmap = QPixmap(image_path)
        self._scale_pixmap()

    def clear_image(self):
        self._pixmap = None
        self.clear()
        self.setText("Нет изображения")

    def resizeEvent(self, event):
        self._scale_pixmap()
        super().resizeEvent(event)

    def _scale_pixmap(self):
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.setPixmap(scaled)
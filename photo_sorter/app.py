import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
from config import create_directories

def main():
    create_directories()  # гарантируем наличие всех папок
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
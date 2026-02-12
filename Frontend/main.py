import sys
import os
import ctypes
from dotenv import load_dotenv
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QSplashScreen, QLabel, QVBoxLayout, QWidget
from PyQt6.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QBrush, QPen

# 1. Load configuration BEFORE importing interfaces
if getattr(sys, 'frozen', False):
    # Running as compiled exe — используем AppData для .env (Program Files защищён от записи)
    appdata_dir = os.path.join(os.environ.get('APPDATA', ''), 'WisperAI')
    os.makedirs(appdata_dir, exist_ok=True)
    env_path = os.path.join(appdata_dir, ".env")
    
    # Если .env не существует, создаём пустой файл
    if not os.path.exists(env_path):
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write("# WisperAI Configuration\n")
            f.write("# GROQ_API_KEY=your_key_here\n")
            f.write("# YANDEX_API_KEY=your_key_here\n")
            f.write("# YANDEX_FOLDER_ID=your_folder_id\n")
            f.write("DEFAULT_MODE=local\n")
            f.write("MODEL_SIZE=small\n")
else:
    # Running as script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir) # Go up one level to C:\Wisper
    env_path = os.path.join(root_dir, ".env")

load_dotenv(env_path, override=True)

# 2. Fix Taskbar Icon
myappid = 'wisper.gui.app.v1' # Arbitrary string
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

from qfluentwidgets import (NavigationItemPosition, FluentWindow, FluentIcon as FIF)
from home_interface import HomeInterface
from transcribe_interface import TranscribeInterface
from settings_interface import SettingsInterface
from version import __version__, __app_name__


class SplashScreen(QWidget):
    """Заставка загрузки приложения"""
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 250)
        
        # Центрируем на экране
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )
        
        self.status_text = "Загрузка..."
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Фон с закруглёнными углами
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.setPen(QPen(QColor(60, 60, 60), 2))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 15, 15)
        
        # Заголовок
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Segoe UI", 28, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(0, 50, 0, 0), Qt.AlignmentFlag.AlignHCenter, "Wisper AI")
        
        # Иконка микрофона (текстовая)
        font_icon = QFont("Segoe UI", 48)
        painter.setFont(font_icon)
        painter.setPen(QColor(100, 180, 255))
        painter.drawText(self.rect().adjusted(0, 100, 0, 0), Qt.AlignmentFlag.AlignHCenter, "🎤")
        
        # Статус загрузки
        font_status = QFont("Segoe UI", 11)
        painter.setFont(font_status)
        painter.setPen(QColor(150, 150, 150))
        painter.drawText(self.rect().adjusted(0, 0, 0, -30), 
                        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, 
                        self.status_text)
    
    def set_status(self, text):
        self.status_text = text
        self.repaint()


class Window(FluentWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f'{__app_name__} v{__version__}')
        
        # Handle icon for both script and frozen exe
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        icon_path = os.path.join(base_path, "assets", "asteroid.ico")
        self.setWindowIcon(QIcon(icon_path))

        # create sub interfaces
        self.homeInterface = HomeInterface(self)
        self.transcribeInterface = TranscribeInterface(self)
        self.settingInterface = SettingsInterface(self)

        # initialize layout
        self.initNavigation()
        self.initWindow()

    def initNavigation(self):
        self.addSubInterface(self.homeInterface, FIF.MICROPHONE, 'Диктовка')
        self.addSubInterface(self.transcribeInterface, FIF.FOLDER, 'Транскрипция')

        self.addSubInterface(self.settingInterface, FIF.SETTING, 'Настройки', NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(900, 700)
        self.setWindowTitle('Wisper AI')

if __name__ == '__main__':
    # Fix High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    
    # Set default font to prevent setPointSize warnings
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Показываем splash screen
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    
    # Обновляем статус и загружаем главное окно
    splash.set_status("Инициализация интерфейса...")
    app.processEvents()
    
    w = Window()
    
    splash.set_status("Готово!")
    app.processEvents()
    
    # Закрываем splash и показываем главное окно
    QTimer.singleShot(300, lambda: (splash.close(), w.show()))
    
    sys.exit(app.exec())

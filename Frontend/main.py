import sys
import os
import ctypes
from dotenv import load_dotenv

# 1. Load configuration BEFORE importing interfaces
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    application_path = os.path.dirname(sys.executable)
    # Assume .env is in the same folder as the exe
    root_dir = application_path
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

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QFont
from qfluentwidgets import (NavigationItemPosition, FluentWindow, FluentIcon as FIF)
from home_interface import HomeInterface
from transcribe_interface import TranscribeInterface
from settings_interface import SettingsInterface

class Window(FluentWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Wisper AI')
        
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
    
    w = Window()
    w.show()
    sys.exit(app.exec())

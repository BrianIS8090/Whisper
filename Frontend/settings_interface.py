from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (SubtitleLabel, BodyLabel, LineEdit, ComboBox, 
                            PrimaryPushButton, CardWidget, InfoBar, InfoBarPosition)
from qfluentwidgets import FluentIcon as FIF
import os
import sys
from dotenv import set_key

def get_env_path():
    """Возвращает путь к .env файлу (AppData для exe, корень проекта для скрипта)"""
    if getattr(sys, 'frozen', False):
        # Скомпилированный exe — используем AppData
        appdata_dir = os.path.join(os.environ.get('APPDATA', ''), 'WisperAI')
        os.makedirs(appdata_dir, exist_ok=True)
        return os.path.join(appdata_dir, ".env")
    else:
        # Запуск как скрипт
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

class SettingsInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingsInterface")
        self.env_path = get_env_path()
        
        self.initUI()
        self.load_settings()
        
    def initUI(self):
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(30, 30, 30, 30)
        self.vBoxLayout.setSpacing(20)

        # Header
        self.titleLabel = SubtitleLabel("Настройки", self)
        self.vBoxLayout.addWidget(self.titleLabel)

        # API Key Card
        self.apiCard = CardWidget(self)
        self.apiLayout = QVBoxLayout(self.apiCard)
        
        self.apiLabel = BodyLabel("Groq API Key", self.apiCard)
        self.apiKeyInput = LineEdit(self.apiCard)
        self.apiKeyInput.setPlaceholderText("gsk_...")
        self.apiKeyInput.setEchoMode(LineEdit.EchoMode.Password)
        
        self.apiLayout.addWidget(self.apiLabel)
        self.apiLayout.addWidget(self.apiKeyInput)
        
        self.vBoxLayout.addWidget(self.apiCard)

        # Yandex API Key Card
        self.yandexCard = CardWidget(self)
        self.yandexLayout = QVBoxLayout(self.yandexCard)
        
        self.yandexLabel = BodyLabel("Yandex API Key (v1/stt)", self.yandexCard)
        self.yandexKeyInput = LineEdit(self.yandexCard)
        self.yandexKeyInput.setPlaceholderText("AQN...")
        self.yandexKeyInput.setEchoMode(LineEdit.EchoMode.Password)
        
        self.yandexLayout.addWidget(self.yandexLabel)
        self.yandexLayout.addWidget(self.yandexKeyInput)
        
        self.yandexFolderLabel = BodyLabel("Yandex Folder ID (обязательно для некоторых ключей)", self.yandexCard)
        self.yandexFolderInput = LineEdit(self.yandexCard)
        self.yandexFolderInput.setPlaceholderText("b1g...")
        
        self.yandexLayout.addWidget(self.yandexFolderLabel)
        self.yandexLayout.addWidget(self.yandexFolderInput)
        
        self.vBoxLayout.addWidget(self.yandexCard)

        # Local Model Card
        self.modelCard = CardWidget(self)
        self.modelLayout = QVBoxLayout(self.modelCard)
        
        self.modelLabel = BodyLabel("Локальная модель Whisper", self.modelCard)
        self.modelComboBox = ComboBox(self.modelCard)
        
        # Populate models with download status
        downloaded = self.get_downloaded_models()
        models = ["tiny", "base", "small", "medium", "large", "turbo"]
        
        for m in models:
            text = m
            if m in downloaded:
                text += " (Скачано)"
            # Important: use userData parameter for clean value
            self.modelComboBox.addItem(text, userData=m)
        
        self.modelLayout.addWidget(self.modelLabel)
        self.modelLayout.addWidget(self.modelComboBox)
        
        self.vBoxLayout.addWidget(self.modelCard)

        # Default Mode Card
        self.modeCard = CardWidget(self)
        self.modeLayout = QVBoxLayout(self.modeCard)
        
        self.modeLabel = BodyLabel("Режим по умолчанию", self.modeCard)
        self.modeComboBox = ComboBox(self.modeCard)
        self.modeComboBox.addItem("Groq API (Облако)", userData="api")
        self.modeComboBox.addItem("Yandex SpeechKit (Облако)", userData="yandex")
        self.modeComboBox.addItem("Локально (Whisper)", userData="local")
        
        self.modeLayout.addWidget(self.modeLabel)
        self.modeLayout.addWidget(self.modeComboBox)
        
        self.vBoxLayout.addWidget(self.modeCard)
        
        # Save Button
        self.saveBtn = PrimaryPushButton(FIF.SAVE, "Сохранить", self)
        self.saveBtn.clicked.connect(self.save_settings)
        self.vBoxLayout.addWidget(self.saveBtn, 0, Qt.AlignmentFlag.AlignLeft)
        
        self.vBoxLayout.addStretch(1)

    def get_downloaded_models(self):
        """Checks standard Whisper cache for existing models."""
        downloaded = []
        try:
            home = os.path.expanduser("~")
            cache_dir = os.path.join(home, ".cache", "whisper")
            
            if os.path.exists(cache_dir):
                files = os.listdir(cache_dir)
                for f in files:
                    if f.endswith(".pt"):
                        for m in ["tiny", "base", "small", "medium", "large", "turbo"]:
                            # Matches filenames like 'small.pt' or hashes starting with 'small'
                            if f.startswith(m):
                                downloaded.append(m)
        except Exception:
            pass
        return list(set(downloaded))

    def load_settings(self):
        api_key = os.getenv("GROQ_API_KEY", "")
        self.apiKeyInput.setText(api_key)
        
        yandex_key = os.getenv("YANDEX_API_KEY", "")
        self.yandexKeyInput.setText(yandex_key)
        
        yandex_folder = os.getenv("YANDEX_FOLDER_ID", "")
        self.yandexFolderInput.setText(yandex_folder)
        
        # Load Model Size (using userData)
        model_size = os.getenv("MODEL_SIZE", "small")
        idx = -1
        for i in range(self.modelComboBox.count()):
            if self.modelComboBox.itemData(i) == model_size:
                idx = i
                break
        if idx != -1:
            self.modelComboBox.setCurrentIndex(idx)
        
        # Load Default Mode
        default_mode = os.getenv("DEFAULT_MODE", "local")
        idx = -1
        for i in range(self.modeComboBox.count()):
            if self.modeComboBox.itemData(i) == default_mode:
                idx = i
                break
        if idx != -1:
            self.modeComboBox.setCurrentIndex(idx)

    def save_settings(self):
        try:
            new_key = self.apiKeyInput.text().strip()
            new_yandex_key = self.yandexKeyInput.text().strip()
            new_folder_id = self.yandexFolderInput.text().strip()
            
            # Get data from itemData instead of text
            new_model = self.modelComboBox.itemData(self.modelComboBox.currentIndex())
            new_mode = self.modeComboBox.itemData(self.modeComboBox.currentIndex())
            
            if not new_model: new_model = "small"
            if not new_mode: new_mode = "local"

            # Create .env if it doesn't exist
            if not os.path.exists(self.env_path):
                with open(self.env_path, 'w') as f:
                    f.write("")
            
            set_key(self.env_path, "GROQ_API_KEY", new_key)
            set_key(self.env_path, "YANDEX_API_KEY", new_yandex_key)
            set_key(self.env_path, "YANDEX_FOLDER_ID", new_folder_id)
            set_key(self.env_path, "MODEL_SIZE", str(new_model))
            set_key(self.env_path, "DEFAULT_MODE", str(new_mode))
            
            # Update session
            os.environ["GROQ_API_KEY"] = new_key
            os.environ["YANDEX_API_KEY"] = new_yandex_key
            os.environ["YANDEX_FOLDER_ID"] = new_folder_id
            os.environ["MODEL_SIZE"] = str(new_model)
            os.environ["DEFAULT_MODE"] = str(new_mode)
            
            InfoBar.success(
                title='Сохранено',
                content=f"Модель: {new_model}, Режим: {new_mode}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title='Ошибка',
                content=str(e),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self
            )

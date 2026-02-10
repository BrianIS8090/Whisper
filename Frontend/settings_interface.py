from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (SubtitleLabel, BodyLabel, LineEdit, ComboBox, 
                            PrimaryPushButton, PushButton, CardWidget, InfoBar, InfoBarPosition)
from qfluentwidgets import FluentIcon as FIF
import os
import sys
import whisper
from dotenv import set_key

MODEL_ALIASES = {
    "tiny": ["tiny", "tiny.en"],
    "base": ["base", "base.en"],
    "small": ["small", "small.en"],
    "medium": ["medium", "medium.en"],
    "large": ["large", "large-v1", "large-v2", "large-v3"],
    "turbo": ["turbo", "large-v3-turbo"]
}

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
        self.populate_model_combo()

        self.modelActionsLayout = QHBoxLayout()
        self.refreshModelsBtn = PushButton(FIF.SYNC, "Обновить статусы", self.modelCard)
        self.refreshModelsBtn.clicked.connect(self.refresh_model_statuses)
        self.deleteModelBtn = PushButton(FIF.DELETE, "Удалить выбранную модель", self.modelCard)
        self.deleteModelBtn.clicked.connect(self.delete_selected_model)
        self.modelActionsLayout.addWidget(self.refreshModelsBtn)
        self.modelActionsLayout.addWidget(self.deleteModelBtn)
        self.modelActionsLayout.addStretch(1)
        
        self.modelLayout.addWidget(self.modelLabel)
        self.modelLayout.addWidget(self.modelComboBox)
        self.modelLayout.addLayout(self.modelActionsLayout)
        
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
        """Определяет, какие модели реально присутствуют в кэше Whisper."""
        downloaded = []
        for model_name in ["tiny", "base", "small", "medium", "large", "turbo"]:
            if self.is_model_downloaded(model_name):
                downloaded.append(model_name)
        return downloaded

    def get_whisper_cache_dir(self):
        default_cache = os.path.join(os.path.expanduser("~"), ".cache")
        return os.path.join(os.getenv("XDG_CACHE_HOME", default_cache), "whisper")

    def get_model_cache_files(self, model_name):
        """Возвращает список возможных файлов кэша для UI-модели."""
        aliases = MODEL_ALIASES.get(model_name, [model_name])
        files = set()
        for alias in aliases:
            model_url = whisper._MODELS.get(alias)
            if model_url:
                files.add(os.path.basename(model_url))
            files.add(f"{alias}.pt")
        return sorted(files)

    def is_model_downloaded(self, model_name):
        cache_dir = self.get_whisper_cache_dir()
        if not os.path.isdir(cache_dir):
            return False
        for filename in self.get_model_cache_files(model_name):
            path = os.path.join(cache_dir, filename)
            if os.path.isfile(path) and os.path.getsize(path) > 0:
                return True
        return False

    def populate_model_combo(self):
        current_model = None
        if hasattr(self, "modelComboBox") and self.modelComboBox.count() > 0:
            current_model = self.modelComboBox.itemData(self.modelComboBox.currentIndex())

        self.modelComboBox.clear()
        downloaded = set(self.get_downloaded_models())
        for model_name in ["tiny", "base", "small", "medium", "large", "turbo"]:
            item_text = model_name
            if model_name in downloaded:
                item_text += " (Скачано)"
            self.modelComboBox.addItem(item_text, userData=model_name)

        if current_model:
            for i in range(self.modelComboBox.count()):
                if self.modelComboBox.itemData(i) == current_model:
                    self.modelComboBox.setCurrentIndex(i)
                    break

    def refresh_model_statuses(self):
        self.populate_model_combo()
        InfoBar.success(
            title='Обновлено',
            content="Статусы локальных моделей обновлены.",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2500,
            parent=self
        )

    def delete_selected_model(self):
        model_name = self.modelComboBox.itemData(self.modelComboBox.currentIndex())
        if not model_name:
            model_name = "small"

        cache_dir = self.get_whisper_cache_dir()
        os.makedirs(cache_dir, exist_ok=True)

        files_to_remove = []
        for filename in self.get_model_cache_files(model_name):
            candidate = os.path.join(cache_dir, filename)
            if os.path.isfile(candidate):
                files_to_remove.append(candidate)

        if not files_to_remove:
            InfoBar.warning(
                title='Нет файлов',
                content=f"Для модели '{model_name}' в кэше ничего не найдено.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self
            )
            return

        errors = []
        removed = 0
        for path in files_to_remove:
            try:
                os.remove(path)
                removed += 1
            except Exception as e:
                errors.append(f"{os.path.basename(path)}: {e}")

        self.populate_model_combo()
        if errors:
            InfoBar.error(
                title='Удалено частично',
                content="; ".join(errors),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=4500,
                parent=self
            )
            return

        InfoBar.success(
            title='Модель удалена',
            content=f"Удалено файлов: {removed}. При следующем запуске модель скачивается заново.",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3500,
            parent=self
        )

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

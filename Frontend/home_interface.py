from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import (SwitchButton, SubtitleLabel, BodyLabel, 
                            TextEdit, InfoBar, InfoBarPosition, CardWidget, IconWidget, ComboBox)
from qfluentwidgets import FluentIcon as FIF
import os
from workers import GlobalSpeechWorker
from dotenv import load_dotenv

class HomeInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("HomeInterface")
        
        # Explicitly reload .env to ensure fresh settings
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(root_dir, ".env")
        load_dotenv(env_path, override=True)
        
        # Debug prints
        mode = os.getenv("DEFAULT_MODE")
        key = os.getenv("GROQ_API_KEY")
        print(f"DEBUG: Loaded .env from {env_path}")
        print(f"DEBUG: DEFAULT_MODE='{mode}'")
        print(f"DEBUG: GROQ_API_KEY found? {bool(key)}")
        
        self.worker = None
        self.thread = None
        
        self.initUI()
        self.initWorker()
        
    def initUI(self):
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(30, 30, 30, 30)
        self.vBoxLayout.setSpacing(20)

        # Header
        self.titleLabel = SubtitleLabel("Глобальная диктовка", self)
        self.vBoxLayout.addWidget(self.titleLabel)

        # Control Card
        self.controlCard = CardWidget(self)
        self.controlCardLayout = QHBoxLayout(self.controlCard)
        self.controlCardLayout.setContentsMargins(20, 20, 20, 20)
        
        self.iconWidget = IconWidget(FIF.MICROPHONE, self.controlCard)
        self.iconWidget.setFixedSize(24, 24)
        
        self.statusLabel = BodyLabel("Служба остановлена", self.controlCard)
        
        # Mode Selection
        self.modeComboBox = ComboBox(self.controlCard)
        self.modeComboBox.addItem("Groq API (Облако)")
        self.modeComboBox.addItem("Yandex SpeechKit (Облако)")
        self.modeComboBox.addItem("Локально (Whisper)")
        self.modeComboBox.setFixedWidth(200)
        
        # Select default based on key availability and settings
        default_mode = os.getenv("DEFAULT_MODE", "local").strip().lower()
        api_key = os.getenv("GROQ_API_KEY")
        yandex_key = os.getenv("YANDEX_API_KEY")
        
        has_groq = bool(api_key)
        has_yandex = bool(yandex_key)
        
        # Determine index
        target_index = 2 # Local default
        if default_mode == "api" and has_groq:
            target_index = 0
        elif default_mode == "yandex" and has_yandex:
            target_index = 1
        
        self.modeComboBox.setCurrentIndex(target_index)
        
        # Disable options if keys are missing (logic could be complex, simple check for now)
        # Ideally, we should use a model to disable specific items, but QComboBox simple API is limited.
        # Users will get an error log if they try to use a missing key.

        self.switchButton = SwitchButton(self.controlCard)
        self.switchButton.setOnText("Включено")
        self.switchButton.setOffText("Выключено")
        self.switchButton.checkedChanged.connect(self.toggle_service)

        self.controlCardLayout.addWidget(self.iconWidget)
        self.controlCardLayout.addSpacing(10)
        self.controlCardLayout.addWidget(self.statusLabel)
        self.controlCardLayout.addStretch(1)
        self.controlCardLayout.addWidget(self.modeComboBox)
        self.controlCardLayout.addSpacing(10)
        self.controlCardLayout.addWidget(self.switchButton)
        
        self.vBoxLayout.addWidget(self.controlCard)

        # Log Area
        self.logLabel = BodyLabel("Журнал событий:", self)
        self.vBoxLayout.addWidget(self.logLabel)
        
        self.logText = TextEdit(self)
        self.logText.setReadOnly(True)
        self.vBoxLayout.addWidget(self.logText)
        
    def initWorker(self):
        model_size = os.getenv("MODEL_SIZE", "small")
        api_key = os.getenv("GROQ_API_KEY")
        yandex_key = os.getenv("YANDEX_API_KEY")
        folder_id = os.getenv("YANDEX_FOLDER_ID")
        
        # Determine initial state
        # Logic: Check combobox index which is already set in initUI
        idx = self.modeComboBox.currentIndex()
        use_groq = (idx == 0)
        use_yandex = (idx == 1)
        
        self.worker = GlobalSpeechWorker(
            api_key=api_key, 
            yandex_key=yandex_key,
            yandex_folder_id=folder_id,
            use_groq=use_groq, 
            use_yandex=use_yandex,
            model_name=model_size
        )
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        
        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.status_changed.connect(self.update_status)
        self.worker.text_ready.connect(self.log_success)
        self.worker.error_occurred.connect(self.log_error)
        
    def toggle_service(self, checked):
        if checked:
            # Update configuration based on ComboBox
            idx = self.modeComboBox.currentIndex()
            is_groq = (idx == 0)
            is_yandex = (idx == 1)
            
            self.worker.use_groq = is_groq
            self.worker.use_yandex = is_yandex
            self.worker.api_key = os.getenv("GROQ_API_KEY")
            self.worker.yandex_key = os.getenv("YANDEX_API_KEY")
            self.worker.yandex_folder_id = os.getenv("YANDEX_FOLDER_ID")
            self.worker.model_name = os.getenv("MODEL_SIZE", "small")
            
            self.modeComboBox.setEnabled(False)
            
            if is_groq:
                mode_text = "Groq API"
            elif is_yandex:
                mode_text = "Yandex SpeechKit"
            else:
                mode_text = f"Whisper {self.worker.model_name}"
            
            self.statusLabel.setText(f"Запуск службы ({mode_text})...")
            self.log_message(f"Запуск службы [{mode_text}]...")
            
            self.switchButton.setEnabled(False)
            self.thread.start()
            self.switchButton.setEnabled(True)
            self.statusLabel.setText("Служба активна (Нажмите F8)")
        else:
            self.statusLabel.setText("Остановка...")
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
            
            self.modeComboBox.setEnabled(True) # Unlock selection
            self.statusLabel.setText("Служба остановлена")
            self.log_message("Служба остановлена.")

    def update_status(self, status):
        if status == "recording":
            self.statusLabel.setText("Запись...")
            self.iconWidget.setIcon(FIF.MICROPHONE)
        elif status == "transcribing":
            self.statusLabel.setText("Распознавание...")
            self.iconWidget.setIcon(FIF.FOLDER)
        else:
            self.statusLabel.setText("Ожидание (F8)")
            self.iconWidget.setIcon(FIF.MICROPHONE)

    def log_message(self, msg):
        self.logText.append(msg)

    def log_success(self, text):
        self.logText.append(f"✅ Распознано: {text}")

    def log_error(self, err):
        self.logText.append(f"❌ Ошибка: {err}")
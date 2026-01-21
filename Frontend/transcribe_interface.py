from PyQt6.QtCore import Qt, QThread
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from qfluentwidgets import (PrimaryPushButton, SubtitleLabel, BodyLabel, 
                            TextEdit, ProgressBar, CardWidget, InfoBar, InfoBarPosition)
from qfluentwidgets import FluentIcon as FIF
import os
from workers import TranscribeWorker
from dotenv import load_dotenv

load_dotenv()

class TranscribeInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("TranscribeInterface")
        self.worker = None
        self.thread = None
        
        self.initUI()
        
    def initUI(self):
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(30, 30, 30, 30)
        self.vBoxLayout.setSpacing(20)

        # Header
        self.titleLabel = SubtitleLabel("Транскрипция файлов", self)
        self.vBoxLayout.addWidget(self.titleLabel)

        # Controls
        self.controlLayout = QHBoxLayout()
        self.fileBtn = PrimaryPushButton(FIF.FOLDER, "Выбрать аудиофайл", self)
        self.fileBtn.clicked.connect(self.select_file)
        self.controlLayout.addWidget(self.fileBtn)
        self.controlLayout.addStretch(1)
        self.vBoxLayout.addLayout(self.controlLayout)
        
        # Progress Bar (Hidden by default)
        self.progressBar = ProgressBar(self)
        self.progressBar.setRange(0, 0) # Indeterminate
        self.progressBar.hide()
        self.vBoxLayout.addWidget(self.progressBar)

        # Result Area
        self.resultLabel = BodyLabel("Результат:", self)
        self.vBoxLayout.addWidget(self.resultLabel)
        
        self.resultText = TextEdit(self)
        self.resultText.setPlaceholderText("Здесь появится текст...")
        self.vBoxLayout.addWidget(self.resultText)
        
    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите аудиофайл", "", "Audio Files (*.mp3 *.wav *.m4a *.flac);;All Files (*.*)"
        )
        
        if file_path:
            self.start_transcription(file_path)

    def start_transcription(self, file_path):
        self.fileBtn.setEnabled(False)
        self.progressBar.show()
        self.resultText.clear()
        
        api_key = os.getenv("GROQ_API_KEY")
        use_groq = bool(api_key)
        model_size = os.getenv("MODEL_SIZE", "small")
        
        self.worker = TranscribeWorker(file_path, api_key=api_key, use_groq=use_groq, model_name=model_size)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_success)
        self.worker.error.connect(self.on_error)
        
        self.thread.start()

    def on_success(self, text):
        self.resultText.setText(text)
        self.stop_thread()
        InfoBar.success(
            title='Готово',
            content="Файл успешно расшифрован.",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self
        )

    def on_error(self, err):
        self.resultText.setText(f"Ошибка: {err}")
        self.stop_thread()
        InfoBar.error(
            title='Ошибка',
            content=str(err),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self
        )

    def stop_thread(self):
        self.fileBtn.setEnabled(True)
        self.progressBar.hide()
        if self.thread:
            self.thread.quit()
            self.thread.wait()

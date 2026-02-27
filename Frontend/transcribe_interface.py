import os
import sys

from dotenv import load_dotenv
from PyQt6.QtCore import Qt, QThread
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SubtitleLabel,
    TextEdit,
)
from qfluentwidgets import FluentIcon as FIF

from workers import TranscribeWorker


def get_env_path():
    """Возвращает путь к .env файлу."""
    if getattr(sys, "frozen", False):
        appdata_dir = os.path.join(os.environ.get("APPDATA", ""), "WisperAI")
        return os.path.join(appdata_dir, ".env")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


class TranscribeInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("TranscribeInterface")
        self.worker = None
        self.thread = None
        self.current_file_path = ""
        self.last_prompt = ""
        self.last_transcription = ""

        load_dotenv(get_env_path(), override=True)
        self.initUI()

    def initUI(self):
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(30, 30, 30, 30)
        self.vBoxLayout.setSpacing(20)

        # Заголовок
        self.titleLabel = SubtitleLabel("Транскрипция файлов", self)
        self.vBoxLayout.addWidget(self.titleLabel)

        # Приписка о текущем движке
        self.engineLabel = BodyLabel("Распознавание работает только через YandexSpeechKit (Async v3).", self)
        self.vBoxLayout.addWidget(self.engineLabel)

        # Поле промта
        self.promptLabel = BodyLabel("Промт для распознавания (опционально):", self)
        self.vBoxLayout.addWidget(self.promptLabel)

        self.promptText = TextEdit(self)
        self.promptText.setPlaceholderText("Например: это интервью, важны названия компаний и имена людей")
        self.promptText.setFixedHeight(90)
        self.vBoxLayout.addWidget(self.promptText)

        # Кнопки управления
        self.controlLayout = QHBoxLayout()
        self.fileBtn = PrimaryPushButton(FIF.FOLDER, "Выбрать аудиофайл", self)
        self.fileBtn.clicked.connect(self.select_file)
        self.controlLayout.addWidget(self.fileBtn)

        self.saveMarkdownBtn = PushButton(FIF.SAVE, "Сохранить как Markdown", self)
        self.saveMarkdownBtn.clicked.connect(self.save_markdown)
        self.saveMarkdownBtn.setEnabled(False)
        self.controlLayout.addWidget(self.saveMarkdownBtn)

        self.controlLayout.addStretch(1)
        self.vBoxLayout.addLayout(self.controlLayout)

        # Индикатор прогресса
        self.progressBar = ProgressBar(self)
        self.progressBar.setRange(0, 0)
        self.progressBar.hide()
        self.vBoxLayout.addWidget(self.progressBar)
        self.statusLabel = BodyLabel("Ожидание файла...", self)
        self.vBoxLayout.addWidget(self.statusLabel)

        # Результат
        self.resultLabel = BodyLabel("Результат:", self)
        self.vBoxLayout.addWidget(self.resultLabel)

        self.resultText = TextEdit(self)
        self.resultText.setPlaceholderText("Здесь появится текст...")
        self.vBoxLayout.addWidget(self.resultText)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите аудиофайл",
            "",
            "Audio Files (*.mp3 *.wav *.ogg *.opus);;All Files (*.*)",
        )

        if file_path:
            self.start_transcription(file_path)

    def start_transcription(self, file_path):
        load_dotenv(get_env_path(), override=True)

        yandex_key = os.getenv("YANDEX_API_KEY", "").strip()
        yandex_folder_id = os.getenv("YANDEX_FOLDER_ID", "").strip()
        prompt_text = self.promptText.toPlainText().strip()

        if not yandex_key:
            self.on_error("Для Yandex SpeechKit не указан ключ YANDEX_API_KEY в настройках.")
            return
        if not yandex_folder_id:
            self.on_error("Для Yandex SpeechKit не указан YANDEX_FOLDER_ID в настройках.")
            return

        self.current_file_path = file_path
        self.last_prompt = prompt_text
        self.last_transcription = ""

        self.fileBtn.setEnabled(False)
        self.saveMarkdownBtn.setEnabled(False)
        self.progressBar.show()
        self.statusLabel.setText("Подготовка асинхронного запроса в YandexSpeechKit...")
        self.resultText.clear()

        self.worker = TranscribeWorker(
            file_path=file_path,
            yandex_key=yandex_key,
            yandex_folder_id=yandex_folder_id,
            prompt=prompt_text,
        )
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.status.connect(self.on_status)
        self.worker.finished.connect(self.on_success)
        self.worker.error.connect(self.on_error)

        self.thread.start()

    def on_success(self, text):
        self.last_transcription = text.strip()
        self.resultText.setText(text)
        self.saveMarkdownBtn.setEnabled(bool(self.last_transcription))
        self.statusLabel.setText("Готово")
        self.stop_thread()
        InfoBar.success(
            title="Готово",
            content="Файл успешно расшифрован.",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self,
        )

    def on_error(self, err):
        error_text = str(err)
        self.resultText.setText(error_text)
        self.saveMarkdownBtn.setEnabled(False)
        self.statusLabel.setText("Ошибка при обработке")
        self.stop_thread()
        InfoBar.error(
            title="Ошибка",
            content="Подробности ошибки выведены в поле результата.",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self,
        )

    def on_status(self, status):
        self.statusLabel.setText(status)

    def save_markdown(self):
        text = self.last_transcription.strip() or self.resultText.toPlainText().strip()
        if not text:
            InfoBar.warning(
                title="Нет данных",
                content="Сначала выполните транскрипцию, затем сохраните результат.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2500,
                parent=self,
            )
            return

        file_name = "transcription.md"
        if self.current_file_path:
            base_name = os.path.splitext(os.path.basename(self.current_file_path))[0]
            file_name = f"{base_name}.md"

        initial_path = file_name
        if self.current_file_path:
            initial_path = os.path.join(os.path.dirname(self.current_file_path), file_name)

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить расшифровку",
            initial_path,
            "Markdown Files (*.md);;All Files (*.*)",
        )
        if not save_path:
            return

        title = os.path.basename(self.current_file_path) if self.current_file_path else "Без имени"
        markdown_lines = [f"# Расшифровка: {title}", ""]
        if self.last_prompt:
            markdown_lines.extend(["## Промт", self.last_prompt, ""])
        markdown_lines.extend(["## Текст", text, ""])
        markdown_content = "\n".join(markdown_lines)

        try:
            with open(save_path, "w", encoding="utf-8") as markdown_file:
                markdown_file.write(markdown_content)
            InfoBar.success(
                title="Сохранено",
                content=f"Markdown сохранён: {save_path}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3500,
                parent=self,
            )
        except Exception as exc:
            InfoBar.error(
                title="Ошибка сохранения",
                content=str(exc),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3500,
                parent=self,
            )

    def stop_thread(self):
        self.fileBtn.setEnabled(True)
        self.progressBar.hide()
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
            self.worker = None

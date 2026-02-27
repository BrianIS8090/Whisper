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

from workers import ChunkedTranscribeWorker


def get_env_path():
  """Возвращает путь к .env файлу."""
  if getattr(sys, "frozen", False):
    appdata_dir = os.path.join(os.environ.get("APPDATA", ""), "WisperAI")
    return os.path.join(appdata_dir, ".env")
  return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


class ChunkedTranscribeInterface(QWidget):
  def __init__(self, parent=None):
    super().__init__(parent=parent)
    self.setObjectName("ChunkedTranscribeInterface")
    self.worker = None
    self.thread = None
    self.current_file_path = ""
    self.last_prompt = ""
    self.last_transcription = ""

    load_dotenv(get_env_path(), override=True)
    self.init_ui()

  def init_ui(self):
    self.v_box_layout = QVBoxLayout(self)
    self.v_box_layout.setContentsMargins(30, 30, 30, 30)
    self.v_box_layout.setSpacing(20)

    self.title_label = SubtitleLabel("Транскрипция больших файлов", self)
    self.v_box_layout.addWidget(self.title_label)

    self.engine_label = BodyLabel(
      "Работает через YandexSpeechKit Async v3: конвертация в mp3 + части до 25MB.",
      self
    )
    self.v_box_layout.addWidget(self.engine_label)

    self.prompt_label = BodyLabel("Промт для постобработки текста (опционально):", self)
    self.v_box_layout.addWidget(self.prompt_label)

    self.prompt_text = TextEdit(self)
    self.prompt_text.setPlaceholderText("Например: исправь пунктуацию и оставь бизнес-термины без изменений")
    self.prompt_text.setFixedHeight(90)
    self.v_box_layout.addWidget(self.prompt_text)

    self.controls_layout = QHBoxLayout()

    self.file_btn = PrimaryPushButton(FIF.FOLDER, "Выбрать файл и обработать", self)
    self.file_btn.clicked.connect(self.select_file)
    self.controls_layout.addWidget(self.file_btn)

    self.save_markdown_btn = PushButton(FIF.SAVE, "Сохранить как Markdown", self)
    self.save_markdown_btn.clicked.connect(self.save_markdown)
    self.save_markdown_btn.setEnabled(False)
    self.controls_layout.addWidget(self.save_markdown_btn)

    self.controls_layout.addStretch(1)
    self.v_box_layout.addLayout(self.controls_layout)

    self.progress_bar = ProgressBar(self)
    self.progress_bar.setRange(0, 0)
    self.progress_bar.hide()
    self.v_box_layout.addWidget(self.progress_bar)

    self.status_label = BodyLabel("Ожидание файла...", self)
    self.v_box_layout.addWidget(self.status_label)

    self.result_label = BodyLabel("Результат:", self)
    self.v_box_layout.addWidget(self.result_label)

    self.result_text = TextEdit(self)
    self.result_text.setPlaceholderText("Здесь появится объединённая расшифровка по всем частям...")
    self.v_box_layout.addWidget(self.result_text)

  def select_file(self):
    file_path, _ = QFileDialog.getOpenFileName(
      self,
      "Выберите аудиофайл",
      "",
      "Audio Files (*.mp3 *.wav *.ogg *.opus *.m4a *.flac);;All Files (*.*)",
    )
    if file_path:
      self.start_transcription(file_path)

  def start_transcription(self, file_path):
    load_dotenv(get_env_path(), override=True)

    yandex_key = os.getenv("YANDEX_API_KEY", "").strip()
    yandex_folder_id = os.getenv("YANDEX_FOLDER_ID", "").strip()
    prompt_text = self.prompt_text.toPlainText().strip()

    if not yandex_key:
      self.on_error("Для Yandex SpeechKit не указан ключ YANDEX_API_KEY в настройках.")
      return
    if not yandex_folder_id:
      self.on_error("Для Yandex SpeechKit не указан YANDEX_FOLDER_ID в настройках.")
      return

    self.current_file_path = file_path
    self.last_prompt = prompt_text
    self.last_transcription = ""

    self.file_btn.setEnabled(False)
    self.save_markdown_btn.setEnabled(False)
    self.progress_bar.show()
    self.status_label.setText("Подготовка пакетной обработки большого файла...")
    self.result_text.clear()

    self.worker = ChunkedTranscribeWorker(
      file_path=file_path,
      yandex_key=yandex_key,
      yandex_folder_id=yandex_folder_id,
      prompt=prompt_text
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
    self.result_text.setText(text)
    self.save_markdown_btn.setEnabled(bool(self.last_transcription))
    self.status_label.setText("Готово")
    self.stop_thread()
    InfoBar.success(
      title="Готово",
      content="Большой файл успешно обработан.",
      orient=Qt.Orientation.Horizontal,
      isClosable=True,
      position=InfoBarPosition.TOP_RIGHT,
      duration=3000,
      parent=self,
    )

  def on_error(self, err):
    self.result_text.setText(str(err))
    self.save_markdown_btn.setEnabled(False)
    self.status_label.setText("Ошибка при обработке")
    self.stop_thread()
    InfoBar.error(
      title="Ошибка",
      content="Подробности ошибки выведены в поле результата.",
      orient=Qt.Orientation.Horizontal,
      isClosable=True,
      position=InfoBarPosition.TOP_RIGHT,
      duration=3500,
      parent=self,
    )

  def on_status(self, status):
    self.status_label.setText(status)

  def save_markdown(self):
    text = self.last_transcription.strip() or self.result_text.toPlainText().strip()
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

    file_name = "large_transcription.md"
    if self.current_file_path:
      base_name = os.path.splitext(os.path.basename(self.current_file_path))[0]
      file_name = f"{base_name}_chunked.md"

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
    markdown_lines = [f"# Расшифровка (большой файл): {title}", ""]
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
    self.file_btn.setEnabled(True)
    self.progress_bar.hide()
    if self.thread:
      self.thread.quit()
      self.thread.wait()
      self.thread = None
      self.worker = None

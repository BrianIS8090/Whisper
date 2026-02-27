import json
import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidget, QVBoxLayout, QHBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
)
from qfluentwidgets import FluentIcon as FIF


def get_dictionary_path():
    """Возвращает путь к пользовательскому словарю."""
    if getattr(sys, "frozen", False):
        appdata_dir = os.path.join(os.environ.get("APPDATA", ""), "WisperAI")
        os.makedirs(appdata_dir, exist_ok=True)
        return os.path.join(appdata_dir, "dictionary.json")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dictionary.json")


class DictionaryInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("DictionaryInterface")
        self.dictionary_path = get_dictionary_path()
        self.entries = []
        self.init_ui()
        self.load_dictionary()

    def init_ui(self):
        self.v_box_layout = QVBoxLayout(self)
        self.v_box_layout.setContentsMargins(30, 30, 30, 30)
        self.v_box_layout.setSpacing(20)

        self.title_label = SubtitleLabel("Словарь нормализации", self)
        self.v_box_layout.addWidget(self.title_label)

        self.help_label = BodyLabel(
            "Добавляйте пары: что распознано -> что вывести. "
            "Пример: «погонные метры» -> «п.м.»",
            self
        )
        self.v_box_layout.addWidget(self.help_label)

        self.form_card = CardWidget(self)
        self.form_layout = QVBoxLayout(self.form_card)
        self.form_layout.setContentsMargins(16, 16, 16, 16)
        self.form_layout.setSpacing(10)

        self.source_label = BodyLabel("Что искать в тексте:", self.form_card)
        self.source_input = LineEdit(self.form_card)
        self.source_input.setPlaceholderText("Например: погонные метры")

        self.target_label = BodyLabel("На что заменить:", self.form_card)
        self.target_input = LineEdit(self.form_card)
        self.target_input.setPlaceholderText("Например: п.м.")

        self.form_layout.addWidget(self.source_label)
        self.form_layout.addWidget(self.source_input)
        self.form_layout.addWidget(self.target_label)
        self.form_layout.addWidget(self.target_input)

        self.buttons_layout = QHBoxLayout()
        self.add_btn = PrimaryPushButton(FIF.ADD, "Добавить/Обновить", self.form_card)
        self.add_btn.clicked.connect(self.add_or_update_entry)
        self.delete_btn = PushButton(FIF.DELETE, "Удалить выбранное", self.form_card)
        self.delete_btn.clicked.connect(self.delete_selected_entry)
        self.save_btn = PushButton(FIF.SAVE, "Сохранить словарь", self.form_card)
        self.save_btn.clicked.connect(self.save_dictionary)

        self.buttons_layout.addWidget(self.add_btn)
        self.buttons_layout.addWidget(self.delete_btn)
        self.buttons_layout.addWidget(self.save_btn)
        self.buttons_layout.addStretch(1)
        self.form_layout.addLayout(self.buttons_layout)
        self.v_box_layout.addWidget(self.form_card)

        self.list_label = BodyLabel("Текущие правила:", self)
        self.v_box_layout.addWidget(self.list_label)

        self.entries_list = QListWidget(self)
        self.entries_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.v_box_layout.addWidget(self.entries_list)

    def show_success(self, message):
        InfoBar.success(
            title="Готово",
            content=message,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2500,
            parent=self,
        )

    def show_error(self, message):
        InfoBar.error(
            title="Ошибка",
            content=message,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3500,
            parent=self,
        )

    def load_dictionary(self):
        if not os.path.exists(self.dictionary_path):
            self.entries = []
            self.refresh_list()
            return
        try:
            with open(self.dictionary_path, "r", encoding="utf-8") as dict_file:
                payload = json.load(dict_file)
            if isinstance(payload, list):
                self.entries = payload
            elif isinstance(payload, dict):
                self.entries = payload.get("entries", [])
                if not isinstance(self.entries, list):
                    self.entries = []
            else:
                self.entries = []
            self.refresh_list()
        except Exception as e:
            self.entries = []
            self.refresh_list()
            self.show_error(f"Не удалось прочитать словарь: {e}")

    def save_dictionary(self):
        try:
            os.makedirs(os.path.dirname(self.dictionary_path), exist_ok=True)
            payload = {"entries": self.entries}
            with open(self.dictionary_path, "w", encoding="utf-8") as dict_file:
                json.dump(payload, dict_file, ensure_ascii=False, indent=2)
            self.show_success(f"Словарь сохранён: {self.dictionary_path}")
        except Exception as e:
            self.show_error(f"Не удалось сохранить словарь: {e}")

    def refresh_list(self):
        self.entries_list.clear()
        for item in self.entries:
            source = str(item.get("source", "")).strip()
            target = str(item.get("target", "")).strip()
            if not source:
                continue
            self.entries_list.addItem(f"{source} -> {target}")

    def find_entry_index(self, source_value):
        source_value = source_value.strip().lower()
        for index, item in enumerate(self.entries):
            source = str(item.get("source", "")).strip().lower()
            if source == source_value:
                return index
        return -1

    def add_or_update_entry(self):
        source_value = self.source_input.text().strip()
        target_value = self.target_input.text().strip()
        if not source_value:
            self.show_error("Заполните поле «Что искать в тексте».")
            return
        if not target_value:
            self.show_error("Заполните поле «На что заменить».")
            return

        entry = {"source": source_value, "target": target_value}
        found_index = self.find_entry_index(source_value)
        if found_index >= 0:
            self.entries[found_index] = entry
        else:
            self.entries.append(entry)

        self.entries.sort(key=lambda item: len(str(item.get("source", ""))), reverse=True)
        self.refresh_list()
        self.save_dictionary()
        self.source_input.clear()
        self.target_input.clear()

    def delete_selected_entry(self):
        selected_items = self.entries_list.selectedItems()
        if not selected_items:
            self.show_error("Сначала выберите правило для удаления.")
            return

        selected_row = self.entries_list.currentRow()
        if selected_row < 0 or selected_row >= len(self.entries):
            self.show_error("Не удалось определить выбранное правило.")
            return

        del self.entries[selected_row]
        self.refresh_list()
        self.save_dictionary()

    def on_selection_changed(self):
        selected_items = self.entries_list.selectedItems()
        if not selected_items:
            return
        selected_row = self.entries_list.currentRow()
        if selected_row < 0 or selected_row >= len(self.entries):
            return

        selected_entry = self.entries[selected_row]
        self.source_input.setText(str(selected_entry.get("source", "")))
        self.target_input.setText(str(selected_entry.get("target", "")))

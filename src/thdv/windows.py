from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QModelIndex
from PySide6.QtCore import QSortFilterProxyModel
from PySide6.QtCore import Qt
from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QAbstractItemView
from PySide6.QtWidgets import QDialog
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QLineEdit
from PySide6.QtWidgets import QListView
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QSplitter
from PySide6.QtWidgets import QTextEdit
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget

from .history import load_manifest_entries
from .loaders import DialogLoader
from .loaders import MessageLoader
from .models import DialogListModel
from .models import MessageListModel
from .rows import DialogRow
from .rows import MessageRow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._dialog_generation = 0
        self._message_generation = 0
        self._dialog_loader: DialogLoader | None = None
        self._message_loader: MessageLoader | None = None

        open_action = QAction('&Open ...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(lambda: self.ask_for_manifest(first_time=False))

        quit_action = QAction('&Quit', self)
        quit_action.setShortcut('Ctrl+Q')
        quit_action.triggered.connect(QApplication.quit)

        file_menu = self.menuBar().addMenu('&File')
        file_menu.addAction(open_action)
        file_menu.addAction(quit_action)

        self.statusBar()

        self.dialog_list_model = DialogListModel()
        self.dialog_list_proxy = QSortFilterProxyModel()
        self.dialog_list_proxy.setSourceModel(self.dialog_list_model)
        self.dialog_list_proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self.dialog_list = QListView()
        self.dialog_list.setUniformItemSizes(True)
        self.dialog_list.setModel(self.dialog_list_proxy)
        self.dialog_list.activated.connect(self._open_dialog_from_index)

        self.dialog_search = QLineEdit()
        self.dialog_search.setPlaceholderText('Search Dialog List')
        self.dialog_search.setClearButtonEnabled(True)
        self.dialog_search.textChanged.connect(self.dialog_list_proxy.setFilterFixedString)

        left_pane = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.dialog_search)
        left_layout.addWidget(self.dialog_list)
        left_pane.setLayout(left_layout)

        self.message_model = MessageListModel()
        self.message_list = QListView()
        self.message_list.setUniformItemSizes(True)
        self.message_list.setModel(self.message_model)
        self.message_list.activated.connect(lambda item: MessageDetail(item).exec())

        self.message_search = QLineEdit()
        self.message_search.setPlaceholderText('Search Messages')
        self.message_search.setClearButtonEnabled(True)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(lambda: self.do_search(self.message_search.text()))
        self.message_search.textChanged.connect(lambda: self.search_timer.start(300))

        self.search_results = QListView()
        self.search_results.hide()
        self.search_results.setUniformItemSizes(True)

        self.message_proxy = QSortFilterProxyModel()
        self.message_proxy.setSourceModel(self.message_model)
        self.message_proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_results.setModel(self.message_proxy)
        self.search_results.activated.connect(self._select_search_result)

        right_pane = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.message_search)
        right_layout.addWidget(self.search_results)
        right_layout.addWidget(self.message_list)
        right_layout.setStretch(1, 1)
        right_layout.setStretch(2, 2)
        right_pane.setLayout(right_layout)

        main_container = QSplitter()
        main_container.addWidget(left_pane)
        main_container.addWidget(right_pane)
        main_container.setStretchFactor(0, 1)
        main_container.setStretchFactor(1, 3)

        self.setCentralWidget(main_container)
        self.resize(1600, 1200)
        self.show()

        for manifest in self._default_manifest_paths():
            if manifest.exists():
                self.set_manifest(manifest)
                break
        else:
            self.ask_for_manifest()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._cancel_dialog_loader()
        self._cancel_message_loader()
        super().closeEvent(event)

    def _default_manifest_paths(self) -> list[Path]:
        program_path = Path(__file__)
        return [
            Path('~/telegram-history-dump/output/progress.json').expanduser(),
            Path('output/progress.json'),
            program_path.resolve().parent / 'output/progress.json',
            program_path.absolute().parent / 'output/progress.json',
        ]

    def ask_for_manifest(self, first_time: bool = True) -> None:
        if first_time:
            info = QMessageBox()
            info.setWindowTitle('Manifest Not Found')
            info.setText('I cannot find telegram-history-dump manifest file (progress.json) at default locations.')
            info.setInformativeText(
                'Press "OK" to select the manifest file (progress.json) manually.\n'
                'Press "Abort" to quit the application.'
            )
            info.setIcon(QMessageBox.Icon.Information)
            info.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Abort)
            info.setDefaultButton(QMessageBox.StandardButton.Ok)
            info_result = info.exec()
            if info_result == QMessageBox.StandardButton.Abort:
                sys.exit(1)

        manifest = QFileDialog.getOpenFileName(
            self,
            'Open Manifest',
            '',
            'progress.json (progress.json)',
        )[0]

        if manifest:
            self.set_manifest(Path(manifest))
        elif first_time:
            self.ask_for_manifest()

    def set_manifest(self, manifest: str | Path) -> None:
        manifest_path = Path(manifest)
        try:
            entries = load_manifest_entries(manifest_path)
        except Exception as exc:
            QMessageBox.critical(self, 'Could Not Open Manifest', str(exc))
            return

        self._cancel_dialog_loader()
        self._cancel_message_loader()
        self._dialog_generation += 1
        self._message_generation += 1

        self.message_search.clear()
        self.search_results.hide()
        self.message_model.reset_for_generation(self._message_generation)
        self.dialog_list_model.reset_for_generation(self._dialog_generation, len(entries))

        full_path = str(manifest_path.resolve())
        self.setWindowTitle(f'{full_path} - thdv')
        self.statusBar().showMessage(f'Loading 0 / {len(entries)} dialogs ...')

        loader = DialogLoader(self._dialog_generation, entries)
        loader.signals.batch_ready.connect(self._on_dialog_batch, Qt.ConnectionType.QueuedConnection)
        loader.signals.progress.connect(self._on_dialog_progress, Qt.ConnectionType.QueuedConnection)
        loader.signals.finished.connect(self._on_dialog_finished, Qt.ConnectionType.QueuedConnection)
        loader.signals.failed.connect(self._on_dialog_failed, Qt.ConnectionType.QueuedConnection)
        self._dialog_loader = loader
        loader.start()

    def _open_dialog_from_index(self, index: QModelIndex) -> None:
        filepath = index.data(Qt.ItemDataRole.UserRole)
        if isinstance(filepath, str):
            self.set_dialog_path(Path(filepath))

    def set_dialog_path(self, path: Path) -> None:
        self._cancel_message_loader()
        self._message_generation += 1
        self.message_search.clear()
        self.search_results.hide()
        self.message_model.reset_for_generation(self._message_generation)
        self.statusBar().showMessage(f'Loading messages from {path} ...')

        loader = MessageLoader(self._message_generation, path)
        loader.signals.batch_ready.connect(self._on_message_batch, Qt.ConnectionType.QueuedConnection)
        loader.signals.progress.connect(self._on_message_progress, Qt.ConnectionType.QueuedConnection)
        loader.signals.finished.connect(self._on_message_finished, Qt.ConnectionType.QueuedConnection)
        loader.signals.failed.connect(self._on_message_failed, Qt.ConnectionType.QueuedConnection)
        self._message_loader = loader
        loader.start()

    def do_search(self, text: str) -> None:
        has_text = bool(text)
        self.search_results.setVisible(has_text)
        self.message_proxy.setFilterFixedString(text if has_text else '')

    def _select_search_result(self, index: QModelIndex) -> None:
        source_index = self.message_proxy.mapToSource(index)
        self.message_list.setCurrentIndex(source_index)
        self.message_list.scrollTo(source_index, QAbstractItemView.ScrollHint.PositionAtCenter)

    def _on_dialog_batch(self, generation: int, rows: list[DialogRow]) -> None:
        self.dialog_list_model.append_rows(generation, rows)

    def _on_dialog_progress(self, generation: int, loaded: int, total: int) -> None:
        if generation == self._dialog_generation:
            self.statusBar().showMessage(f'Loading {loaded} / {total} dialogs ...')

    def _on_dialog_finished(self, generation: int, loaded: int, cancelled: bool) -> None:
        if generation != self._dialog_generation:
            return
        if cancelled:
            self.statusBar().showMessage(f'Cancelled after loading {loaded} dialogs.')
            return
        self._dialog_loader = None
        self.statusBar().showMessage(f'Total: {loaded} dialogs.')

    def _on_dialog_failed(self, generation: int, error: str) -> None:
        if generation == self._dialog_generation:
            QMessageBox.critical(self, 'Could Not Load Dialogs', error)
            self.statusBar().showMessage('Dialog loading failed.')

    def _on_message_batch(self, generation: int, rows: list[MessageRow]) -> None:
        self.message_model.append_rows(generation, rows)

    def _on_message_progress(self, generation: int, loaded: int) -> None:
        if generation == self._message_generation:
            self.statusBar().showMessage(f'Loading {loaded} messages ...')

    def _on_message_finished(self, generation: int, loaded: int, cancelled: bool) -> None:
        if generation != self._message_generation:
            return
        if cancelled:
            self.statusBar().showMessage(f'Cancelled after loading {loaded} messages.')
            return
        self._message_loader = None
        self.statusBar().showMessage(f'Total: {loaded} messages.')

    def _on_message_failed(self, generation: int, error: str) -> None:
        if generation == self._message_generation:
            QMessageBox.critical(self, 'Could Not Load Messages', error)
            self.statusBar().showMessage('Message loading failed.')

    def _cancel_dialog_loader(self) -> None:
        if self._dialog_loader:
            self._dialog_loader.cancel()
            self._dialog_loader = None

    def _cancel_message_loader(self) -> None:
        if self._message_loader:
            self._message_loader.cancel()
            self._message_loader = None


class MessageDetail(QDialog):
    def __init__(self, item: QModelIndex) -> None:
        super().__init__()

        message = QTextEdit()
        message.setReadOnly(True)
        display_text = item.data(Qt.ItemDataRole.DisplayRole)
        message.setPlainText(display_text if isinstance(display_text, str) else '')

        event = QTextEdit()
        event.setReadOnly(True)
        raw_event = item.data(Qt.ItemDataRole.UserRole)
        event_pretty = json.dumps(
            raw_event if isinstance(raw_event, dict) else {},
            indent=2,
            ensure_ascii=False,
        )
        event.setMarkdown(f'```\n{event_pretty}\n```')

        layout = QVBoxLayout(self)
        layout.addWidget(message)
        layout.addWidget(event)
        self.setLayout(layout)
        self.resize(800, 600)
        self.setWindowTitle('Message Detail')

from pathlib import Path
from threading import Event
from threading import Thread

from PySide6.QtCore import Signal
from PySide6.QtCore import QObject

from .rows import DialogRow
from .rows import MessageRow
from .rows import DialogManifestEntry
from .history import format_message
from .history import read_json_line
from .history import build_dialog_row

DIALOG_BATCH_SIZE = 25
MESSAGE_BATCH_SIZE = 1_000


class DialogLoaderSignals(QObject):
    batch_ready = Signal(int, object)
    progress = Signal(int, int, int)
    finished = Signal(int, int, bool)
    failed = Signal(int, str)


class MessageLoaderSignals(QObject):
    batch_ready = Signal(int, object)
    progress = Signal(int, int)
    finished = Signal(int, int, bool)
    failed = Signal(int, str)


class DialogLoader:
    def __init__(
        self,
        generation: int,
        entries: list[DialogManifestEntry],
        batch_size: int = DIALOG_BATCH_SIZE,
    ) -> None:
        self.generation = generation
        self.entries = entries
        self.batch_size = batch_size
        self.signals = DialogLoaderSignals()
        self._cancelled = Event()
        self._thread = Thread(target=self._run, name='thdv-dialog-loader', daemon=True)

    def start(self) -> None:
        self._thread.start()

    def cancel(self) -> None:
        self._cancelled.set()

    def _run(self) -> None:
        loaded = 0
        try:
            batch: list[DialogRow] = []
            total = len(self.entries)

            for entry in self.entries:
                if self._cancelled.is_set():
                    break

                batch.append(build_dialog_row(entry))
                loaded += 1

                if len(batch) >= self.batch_size:
                    self.signals.batch_ready.emit(self.generation, batch)
                    self.signals.progress.emit(self.generation, loaded, total)
                    batch = []

            if batch and not self._cancelled.is_set():
                self.signals.batch_ready.emit(self.generation, batch)
                self.signals.progress.emit(self.generation, loaded, total)

            self.signals.finished.emit(self.generation, loaded, self._cancelled.is_set())
        except Exception as exc:
            self.signals.failed.emit(self.generation, str(exc))


class MessageLoader:
    def __init__(
        self,
        generation: int,
        path: Path,
        batch_size: int = MESSAGE_BATCH_SIZE,
    ) -> None:
        self.generation = generation
        self.path = path
        self.batch_size = batch_size
        self.signals = MessageLoaderSignals()
        self._cancelled = Event()
        self._thread = Thread(target=self._run, name='thdv-message-loader', daemon=True)

    def start(self) -> None:
        self._thread.start()

    def cancel(self) -> None:
        self._cancelled.set()

    def _run(self) -> None:
        loaded = 0
        try:
            batch: list[MessageRow] = []
            with self.path.open(encoding='utf-8') as f:
                for line in f:
                    if self._cancelled.is_set():
                        break

                    event = read_json_line(line)
                    if not event:
                        continue

                    batch.append(MessageRow(display=format_message(event), event=event))
                    loaded += 1

                    if len(batch) >= self.batch_size:
                        self.signals.batch_ready.emit(self.generation, batch)
                        self.signals.progress.emit(self.generation, loaded)
                        batch = []

            if batch and not self._cancelled.is_set():
                self.signals.batch_ready.emit(self.generation, batch)
                self.signals.progress.emit(self.generation, loaded)

            self.signals.finished.emit(self.generation, loaded, self._cancelled.is_set())
        except Exception as exc:
            self.signals.failed.emit(self.generation, str(exc))

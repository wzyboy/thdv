from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtCore import QModelIndex
from PySide6.QtCore import QAbstractListModel
from PySide6.QtCore import QPersistentModelIndex

from .rows import DialogRow
from .rows import MessageRow


class DialogListModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self._generation = 0
        self._items: list[DialogRow] = []
        self._total = 0

    def reset_for_generation(self, generation: int, total: int) -> None:
        self.beginResetModel()
        self._generation = generation
        self._items = []
        self._total = total
        self.endResetModel()

    def append_rows(self, generation: int, rows: list[DialogRow]) -> bool:
        if generation != self._generation or not rows:
            return False

        start = len(self._items)
        self.beginInsertRows(QModelIndex(), start, start + len(rows) - 1)
        self._items.extend(rows)
        self.endInsertRows()
        return True

    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if not index.isValid():
            return None

        row = index.row()
        if row < 0 or row >= len(self._items):
            return None

        item = self._items[row]
        if role == Qt.ItemDataRole.DisplayRole:
            return item.name
        if role == Qt.ItemDataRole.ToolTipRole:
            return item.peer_id
        if role == Qt.ItemDataRole.UserRole:
            return str(item.filepath)

        return None


class MessageListModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self._generation = 0
        self._rows: list[MessageRow] = []

    def reset_for_generation(self, generation: int) -> None:
        self.beginResetModel()
        self._generation = generation
        self._rows = []
        self.endResetModel()

    def append_rows(self, generation: int, rows: list[MessageRow]) -> bool:
        if generation != self._generation or not rows:
            return False

        start = len(self._rows)
        self.beginInsertRows(QModelIndex(), start, start + len(rows) - 1)
        self._rows.extend(rows)
        self.endInsertRows()
        return True

    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | dict[str, Any] | None:
        if not index.isValid():
            return None

        row = index.row()
        if row < 0 or row >= len(self._rows):
            return None

        item = self._rows[row]
        if role == Qt.ItemDataRole.DisplayRole:
            return item.display
        if role == Qt.ItemDataRole.UserRole:
            return item.event

        return None

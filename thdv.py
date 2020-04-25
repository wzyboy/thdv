#!/usr/bin/env python

import os
import sys
import json
import signal
from datetime import datetime
from collections import namedtuple

from PyQt5.QtCore import (
    Qt, pyqtSignal,
    QAbstractListModel, QModelIndex,
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QAction,
    QSplitter, QVBoxLayout,
    QLineEdit,
    QListView,
)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # Menu.
        quitAction = QAction('&Quit', self)
        quitAction.setShortcut('Ctrl+Q')
        quitAction.triggered.connect(QApplication.quit)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(quitAction)

        # Status.
        self.statusBar()

        # Left pane.
        self.searchBar = QLineEdit()
        self.dialogList = QListView()
        self.dialogList.setModel(DialogList('./output/progress.json'))  # FIXME
        self.dialogList.activated.connect(self.loadDialog)
        self.dialogList.model().status.connect(self.statusBar().showMessage)

        leftPane = QWidget()
        leftPaneLayout = QVBoxLayout()
        leftPaneLayout.addWidget(self.searchBar)
        leftPaneLayout.addWidget(self.dialogList)
        leftPane.setLayout(leftPaneLayout)

        # Right pane.
        self.dialog = QListView()
        self.dialog.setModel(Dialog())
        self.dialog.model().status.connect(self.statusBar().showMessage)

        rightPane = QWidget()
        rightPaneLayout = QVBoxLayout()
        rightPaneLayout.addWidget(self.dialog)
        rightPane.setLayout(rightPaneLayout)

        # Layouts.
        mainContainer = QSplitter()
        mainContainer.addWidget(leftPane)
        mainContainer.addWidget(rightPane)
        mainContainer.setStretchFactor(0, 1)
        mainContainer.setStretchFactor(1, 3)

        # Display the window.
        self.setCentralWidget(mainContainer)
        self.setWindowFlag(Qt.Dialog)
        self.resize(800, 600)
        self.show()

    def loadDialog(self, item):
        path = item.data(Qt.UserRole)
        self.dialog.model().setPath(path)


def format_message(event):

    event_type = event['event']
    if event_type not in ('message', 'service'):
        return event

    tpl = '[{timestamp}] {from_name}: {payload}'

    timestamp = datetime.fromtimestamp(event['date']).strftime('%Y-%m-%d %H:%M:%S')
    try:
        from_name = '{} {}'.format(event['from']['first_name'], event['from']['last_name']).strip()
    except KeyError:
        from_name = 'user#{}'.format(event['from']['peer_id'])
    payload = event.get(
        'text',
        event.get(
            'media',
            event.get(
                'action'
            )
        )
    )
    msg = tpl.format(timestamp=timestamp, from_name=from_name, payload=payload)
    return msg


def get_print_name(peer_id, filename):
    with open(filename, 'r') as f:
        for line in f:
            event = json.loads(line)
            from_ = event['from']
            to = event['to']
            if str(to['peer_id']) == peer_id:
                print_name = to['print_name'] or f'{to["peer_type"]}#{to["peer_id"]}'
                return print_name
            if str(from_['peer_id']) == peer_id:
                print_name = from_['print_name'] or f'{from_["peer_type"]}#{from_["peer_id"]}'
                return print_name
        else:
            return 'UNKNOWN'


DialogInfo = namedtuple('DialogInfo', 'id filepath name')


class DialogList(QAbstractListModel):

    status = pyqtSignal(str)

    def __init__(self, manifest):
        super().__init__()
        self.eof = False
        with open(manifest, 'r') as f:
            data = json.load(f)
        self.dialogs = sorted(
            data['dialogs'].items(),
            key=lambda x: x[1]['newest_date'],
            reverse=True
        )
        manifest_dir = os.path.dirname(manifest)
        self.peer_fn = iter([
            (k, os.path.join(manifest_dir, v['dumper_state']['outfile']))
            for k, v in self.dialogs
        ])
        self.items = []

    def rowCount(self, parent):
        return len(self.items)

    def canFetchMore(self, parent):
        return not self.eof

    def fetchMore(self, parent):
        pairs = []
        for i in range(5):
            try:
                pair = next(self.peer_fn)
            except StopIteration:
                self.eof = True
            else:
                pairs.append(pair)

        if not pairs:
            return

        self.beginInsertRows(parent, len(self.items), len(self.items) + len(pairs) - 1)

        for peer, fn in pairs:
            self.status.emit(f'Parsing members from {fn} ...')
            name = get_print_name(peer, fn)
            dialogInfo = DialogInfo(peer, fn, name)
            self.items.append(dialogInfo)

        self.endInsertRows()

    def data(self, index, role=Qt.DisplayRole):
        if not self.items:
            return

        if role == Qt.DisplayRole:
            return self.items[index.row()].name
        elif role == Qt.ToolTipRole:
            return self.items[index.row()].id
        elif role == Qt.UserRole:
            return self.items[index.row()].filepath


class Dialog(QAbstractListModel):

    status = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.fd = None
        self.eof = False
        self.messages = []

    def setPath(self, path):
        self.beginResetModel()

        if self.fd:
            self.fd.close()
        self.fd = open(path, 'r')
        self.eof = False
        self.messages = []
        self.status.emit(path)

        self.endResetModel()

    def rowCount(self, parent):
        return len(self.messages)

    def canFetchMore(self, parent):
        # Always try to fetch more, unless exception raised
        return bool(self.fd and not self.eof)

    def fetchMore(self, parent):
        lines = []
        for i in range(1000):
            try:
                line = next(self.fd)
            except StopIteration:
                self.eof = True
            else:
                lines.append(line)

        if not lines:
            return

        self.beginInsertRows(parent, len(self.messages), len(self.messages) + len(lines) - 1)

        for line in lines:
            event = json.loads(line)
            message = format_message(event)
            self.messages.append(message)

        if self.canFetchMore(QModelIndex()):
            self.status.emit(f'Total: {len(self.messages)}+ messages.')
        else:
            self.status.emit(f'Total: {len(self.messages)} messages.')

        self.endInsertRows()

    def data(self, index, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return
        if not self.fd:
            return

        message = self.messages[index.row()]
        return message


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    window = MainWindow()
    app.exec()

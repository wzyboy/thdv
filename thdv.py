#!/usr/bin/env python3

import os
import sys
import json
import signal
from datetime import datetime
from collections import namedtuple

from PyQt5.QtCore import (
    Qt, pyqtSignal, QTimer,
    QAbstractListModel, QModelIndex,
    QSortFilterProxyModel,
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QDialog, QFileDialog, QMessageBox,
    QTextEdit,
    QAction,
    QSplitter, QVBoxLayout,
    QLineEdit,
    QListView,
)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # Menu.
        openAction = QAction('&Open ...', self)
        openAction.setShortcut('Ctrl+O')
        openAction.triggered.connect(lambda: self.askForManifest(firstTime=False))
        quitAction = QAction('&Quit', self)
        quitAction.setShortcut('Ctrl+Q')
        quitAction.triggered.connect(QApplication.quit)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openAction)
        fileMenu.addAction(quitAction)

        # Status.
        self.statusBar()

        # Left pane.
        self.dialogList = QListView()
        self.dialogList.setUniformItemSizes(True)
        self.dialogListProxy = QSortFilterProxyModel()
        self.dialogList.setModel(self.dialogListProxy)
        self.dialogList.activated.connect(lambda item: self.dialogModel.setPath(item.data(Qt.UserRole)))

        self.searchBar1 = QLineEdit()
        self.searchBar1.setPlaceholderText('Search Dialog list')
        self.searchBar1.setClearButtonEnabled(True)
        self.dialogListProxy.setFilterCaseSensitivity(False)
        self.searchBar1.textChanged.connect(self.dialogListProxy.setFilterFixedString)

        self.leftPane = QWidget()
        self.leftPaneLayout = QVBoxLayout()
        self.leftPaneLayout.addWidget(self.searchBar1)
        self.leftPaneLayout.addWidget(self.dialogList)
        self.leftPane.setLayout(self.leftPaneLayout)

        # Right pane.
        self.dialog = QListView()
        self.dialog.setUniformItemSizes(True)
        self.dialogModel = Dialog()
        self.dialogModel.status.connect(self.statusBar().showMessage)
        self.dialog.setModel(self.dialogModel)
        self.dialog.activated.connect(lambda item: MessageDetail(item).exec())

        self.searchBar2 = QLineEdit()
        self.searchBar2.setPlaceholderText('Search Messages')
        self.searchBar2.setClearButtonEnabled(True)
        self.typingTimer2 = QTimer()
        self.typingTimer2.setSingleShot(True)
        self.typingTimer2.timeout.connect(lambda: self.doSearch(self.searchBar2.text()))
        self.searchBar2.textChanged.connect(lambda: self.typingTimer2.start(500))

        self.searchResults = QListView()
        self.searchResults.hide()
        self.searchResults.setUniformItemSizes(True)
        self.dialogProxy = QSortFilterProxyModel()
        self.dialogProxy.setSourceModel(self.dialogModel)
        self.dialogProxy.setFilterCaseSensitivity(False)
        self.searchResults.setModel(self.dialogProxy)
        self.searchResults.activated.connect(lambda item: self.dialog.setCurrentIndex(self.dialogProxy.mapToSource(item)))
        self.searchResults.activated.connect(
            lambda item: self.dialog.scrollTo(
                self.dialogProxy.mapToSource(item), QListView.PositionAtCenter
            )
        )

        self.rightPane = QWidget()
        self.rightPaneLayout = QVBoxLayout()
        self.rightPaneLayout.addWidget(self.searchBar2)
        self.rightPaneLayout.addWidget(self.searchResults)
        self.rightPaneLayout.addWidget(self.dialog)
        self.rightPaneLayout.setStretch(1, 1)
        self.rightPaneLayout.setStretch(2, 2)
        self.rightPane.setLayout(self.rightPaneLayout)

        # Layouts.
        mainContainer = QSplitter()
        mainContainer.addWidget(self.leftPane)
        mainContainer.addWidget(self.rightPane)
        mainContainer.setStretchFactor(0, 1)
        mainContainer.setStretchFactor(1, 3)

        # Display the window.
        self.setCentralWidget(mainContainer)
        self.resize(1600, 1200)
        self.show()

        # Ask for manifest location if default path does not exist
        manifest = './output/progress.json'
        if not os.path.exists(manifest):
            self.askForManifest()
        else:
            self.setManifest(manifest)

    def askForManifest(self, firstTime=True):
        if firstTime:
            info = QMessageBox()
            info.setWindowTitle('Manifest Not Found')
            info.setText('telegram-history-dump manifest file required. (Default: ./output/progress.json)')
            info.setInformativeText(
                'Press "OK" to select the manifest file (progress.json) manually.\n'
                'Press "Abort" to quit the application.'
            )
            info.setIcon(QMessageBox.Information)
            info.setStandardButtons(QMessageBox.Ok | QMessageBox.Abort)
            info.setDefaultButton(QMessageBox.Ok)
            infoRc = info.exec()
            if infoRc == QMessageBox.Abort:
                sys.exit(1)

        manifest = QFileDialog.getOpenFileName(filter='progress.json (progress.json)')[0]

        if manifest:
            self.setManifest(manifest)
        else:
            # When invoked by File -> Open menu, bail out if user does not select anything
            if firstTime:
                self.askForManifest()

    def setManifest(self, manifest):
        self.dialogListModel = DialogList(manifest)
        self.dialogListModel.status.connect(self.statusBar().showMessage)
        self.dialogListProxy.setSourceModel(self.dialogListModel)
        fullPath = os.path.abspath(manifest)
        self.setWindowTitle(f'{fullPath} - thdv')

    def doSearch(self, text):
        hasText = bool(text)
        self.searchResults.setVisible(hasText)
        if hasText:
            self.dialogProxy.setFilterFixedString(text)


class MessageDetail(QDialog):

    def __init__(self, item):
        super().__init__()

        message = QTextEdit()
        message.setReadOnly(True)
        message.setPlainText(item.data())

        event = QTextEdit()
        event.setReadOnly(True)
        eventPretty = json.dumps(item.data(Qt.UserRole), indent=2, ensure_ascii=False)
        eventMarkdown = f'```\n{eventPretty}\n```'
        event.setMarkdown(eventMarkdown)

        layout = QVBoxLayout(self)
        layout.addWidget(message)
        layout.addWidget(event)
        self.setLayout(layout)
        self.resize(800, 600)
        self.setWindowTitle('Message Detail')


def format_message(event):

    event_type = event['event']
    if event_type not in ('message', 'service'):
        return event

    timestamp = datetime.fromtimestamp(event['date']).strftime('%Y-%m-%d %H:%M:%S')
    try:
        from_name = '{} {}'.format(event['from']['first_name'], event['from']['last_name']).strip()
    except KeyError:
        from_name = '{}#{}'.format(event['from']['peer_type'], event['from']['peer_id'])
    fwd_from = event.get('fwd_from')
    if fwd_from:
        try:
            fwd = ' [FWD: {} {}]'.format(fwd_from['first_name'], fwd_from['last_name']).strip()
        except KeyError:
            fwd = ' [FWD: {}#{}]'.format(fwd_from['peer_type'], fwd_from['peer_id'])
    else:
        fwd = ''
    payload = event.get(
        'text',
        event.get(
            'media',
            event.get(
                'action'
            )
        )
    )

    msg = f'[{timestamp}] {from_name}{fwd}: {payload}'
    return msg


def get_print_name(peer_id, filename):
    with open(filename, 'r', encoding='utf-8') as f:
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
        with open(manifest, 'r', encoding='utf-8') as f:
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
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.fetchMore(QModelIndex()))
        self.timer.start(100)

    def rowCount(self, parent):
        return len(self.items)

    def canFetchMore(self, parent):
        return not self.eof

    def fetchMore(self, parent):
        pairs = []
        for i in range(100):
            try:
                pair = next(self.peer_fn)
            except StopIteration:
                self.eof = True
                self.timer.stop()
            else:
                pairs.append(pair)

        if not pairs:
            return

        self.beginInsertRows(parent, len(self.items), len(self.items) + len(pairs) - 1)

        for peer, fn in pairs:
            name = get_print_name(peer, fn)
            dialogInfo = DialogInfo(peer, fn, name)
            self.items.append(dialogInfo)

        if self.canFetchMore(QModelIndex()):
            self.status.emit(f'Total: {len(self.items)}+ dialogs.')
        else:
            self.status.emit(f'Total: {len(self.items)} dialogs.')

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
        self.events = []
        self.messages = []
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.fetchMore(QModelIndex()))

    def setPath(self, path):
        self.beginResetModel()

        if self.fd:
            self.fd.close()
        self.fd = open(path, 'r', encoding='utf-8')
        self.eof = False
        self.events = []
        self.messages = []
        self.status.emit(path)
        self.timer.start(100)

        self.endResetModel()

    def rowCount(self, parent):
        return len(self.messages)

    def canFetchMore(self, parent):
        # Always try to fetch more, unless exception raised
        return bool(self.fd and not self.eof)

    def fetchMore(self, parent):
        lines = []
        for i in range(10000):
            try:
                line = next(self.fd)
            except StopIteration:
                self.eof = True
                self.timer.stop()
            else:
                lines.append(line)

        if not lines:
            return

        self.beginInsertRows(parent, len(self.messages), len(self.messages) + len(lines) - 1)

        for line in lines:
            event = json.loads(line)
            message = format_message(event)
            self.events.append(event)
            self.messages.append(message)

        if self.canFetchMore(QModelIndex()):
            self.status.emit(f'Total: {len(self.messages)}+ messages.')
        else:
            self.status.emit(f'Total: {len(self.messages)} messages.')

        self.endInsertRows()

    def data(self, index, role=Qt.DisplayRole):
        if not self.fd:
            return
        if role == Qt.DisplayRole:
            return self.messages[index.row()]
        elif role == Qt.UserRole:
            return self.events[index.row()]


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    window = MainWindow()
    app.exec()

#!/usr/bin/env python

import os
import sys
import json
import signal
from datetime import datetime
from collections import OrderedDict
from collections.abc import Mapping

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QAction,
    QGridLayout, QVBoxLayout,
    QLineEdit, QListWidget,
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
        self.diaglogList = QListWidget()
        self.populateDialogList()
        self.diaglogList.itemActivated.connect(self.loadDialog)

        leftPane = QVBoxLayout()
        leftPane.addWidget(self.searchBar)
        leftPane.addWidget(self.diaglogList)

        # Right pane.
        self.chat = QListWidget()

        rightPane = QVBoxLayout()
        rightPane.addWidget(self.chat)

        # Layouts.
        mainLayout = QGridLayout()
        mainLayout.addLayout(leftPane, 0, 0)
        mainLayout.addLayout(rightPane, 0, 1)
        mainContainer = QWidget()
        mainContainer.setLayout(mainLayout)

        # Display the window.
        self.setCentralWidget(mainContainer)
        self.setWindowFlag(Qt.Dialog)
        self.resize(800, 600)
        self.show()

    def populateDialogList(self):
        self.dm = DialogManager('./output/progress.json')  # FIXME
        self.diaglogList.addItems(self.dm)

    def loadDialog(self, item):
        dialogId = item.text()
        dialogPath = self.dm[dialogId]
        with open(dialogPath, 'r') as f:
            events = [json.loads(line) for line in f]
        messages = [format_message(event) for event in events]
        self.chat.clear()
        self.chat.addItems(messages)


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


class DialogManager(Mapping):

    def __init__(self, manifest):
        with open(manifest, 'r') as f:
            data = json.load(f)
        self.dialogs = sorted(
            data['dialogs'].items(),
            key=lambda x: x[1]['newest_date'],
            reverse=True
        )
        manifest_dir = os.path.dirname(manifest)
        self.peer_fn = OrderedDict((
            (k, os.path.join(manifest_dir, v['dumper_state']['outfile']))
            for k, v in self.dialogs
        ))

    def __getitem__(self, k):
        return self.peer_fn[k]

    def __iter__(self):
        return iter(self.peer_fn)

    def __len__(self):
        return len(self.peer_fn)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    window = MainWindow()
    app.exec()
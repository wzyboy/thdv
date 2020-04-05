#!/usr/bin/env python

import sys
import signal

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QAction,
    QGridLayout, QVBoxLayout,
    QLineEdit, QListView,
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
        searchBar = QLineEdit()
        diaglogList = QListView()

        leftPane = QVBoxLayout()
        leftPane.addWidget(searchBar)
        leftPane.addWidget(diaglogList)

        # Right pane.
        chat = QListView()

        rightPane = QVBoxLayout()
        rightPane.addWidget(chat)

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


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    window = MainWindow()
    app.exec()

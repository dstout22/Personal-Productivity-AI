#
# To reload shortcut: 
#
# .\.venv\Scripts\Activate.ps1
# pyinstaller --onefile --windowed --clean main.py
#

import sys

from ai import ask_ai

from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit, QLineEdit
from PySide6.QtCore import Qt

from database import initialize_database

initialize_database()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Personal Productivity AI")
        self.resize(800, 600)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message...")
        self.input.returnPressed.connect(self.send_message)

        self.setCentralWidget(self.chat)

        self.input.setParent(self)
        self.input.setGeometry(10, 550, 780, 40)

    def send_message(self):
        message = self.input.text()

        if not message:
            return

        self.chat.append(f"> {message}")
        self.input.clear()

        response = ask_ai(message)
        self.chat.append(response)

app = QApplication(sys.argv)

window = MainWindow()
window.show()

sys.exit(app.exec())
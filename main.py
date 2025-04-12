import sys

from PyQt5.QtWidgets import QApplication

from app_window import TextToSpeechApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = TextToSpeechApp()
    ex.show()
    sys.exit(app.exec_())

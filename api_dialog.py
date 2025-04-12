from PyQt5.QtWidgets import (
    QDialog,
    QLineEdit,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
)


# --- APIキー管理ダイアログ ---
class ApiKeyDialog(QDialog):
    """APIキーを入力・保存するためのダイアログ"""

    def __init__(self, parent=None, current_api_key=""):
        super().__init__(parent)
        self.setWindowTitle("APIキー設定")
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Google Cloud APIキーを入力してください")
        if current_api_key:
            self.api_key_input.setText(current_api_key)  # 初期値を設定

        layout = QFormLayout(self)
        layout.addRow("APIキー:", self.api_key_input)

        button_layout = QHBoxLayout()
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.accept)  # OKボタンが押されたらaccept
        cancel_button = QPushButton("キャンセル")
        cancel_button.clicked.connect(self.reject)  # Cancelボタンが押されたらreject
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addRow(button_layout)

    def get_api_key(self):
        """入力されたAPIキーを取得する"""
        return self.api_key_input.text().strip()

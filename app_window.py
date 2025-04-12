import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QSlider,
    QFileDialog,
    QMessageBox,
    QSpinBox,
)
from dotenv import load_dotenv, set_key

# 他のモジュールからクラスをインポート
from api_dialog import ApiKeyDialog
from conversion_thread import ConversionThread

# --- 定数 ---
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "results"
ENV_FILE_PATH = Path(__file__).parent / ".env"
API_KEY_NAME = "GOOGLE_CLOUD_API_KEY"  # .env ファイルでのキー名


# --- メインウィンドウ ---
class TextToSpeechApp(QWidget):
    def __init__(self):
        super().__init__()
        self.api_key = None
        self.input_file_path = ""
        self.output_dir_path = str(DEFAULT_OUTPUT_DIR)
        self.last_output_path = None  # 再生するファイルのパスを保持
        self.init_ui()

    def load_api_key(self):
        """.env ファイルからAPIキーを読み込む"""
        load_dotenv(dotenv_path=ENV_FILE_PATH)
        self.api_key = os.getenv(API_KEY_NAME)
        # print(f"Loaded API Key: {self.api_key}") # デバッグ用

    def save_api_key(self, key):
        """.env ファイルにAPIキーを保存する"""
        try:
            # .envファイルが存在しない場合は作成
            if not ENV_FILE_PATH.exists():
                ENV_FILE_PATH.touch()
            # キーを保存 (ファイルが存在しない場合やキーが存在しない場合は新規作成、存在する場合は上書き)
            # quote_mode='never' を指定して不要なクォートを防ぐ
            set_key(str(ENV_FILE_PATH), API_KEY_NAME, key, quote_mode="never")
            self.api_key = key  # アプリケーション内のキーも更新
            QMessageBox.information(self, "成功", "APIキーを保存しました。")
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"APIキーの保存に失敗しました: {e}")

    def show_api_key_dialog(self):
        """APIキー設定ダイアログを表示する"""
        # .envファイルから最新のキーを読み込む試み
        self.load_api_key()
        dialog = ApiKeyDialog(self, current_api_key=self.api_key)  # 現在のキーを渡す
        if dialog.exec_():  # OKボタンが押された場合
            api_key = dialog.get_api_key()
            if api_key:
                self.save_api_key(api_key)
            else:
                QMessageBox.warning(self, "警告", "APIキーが入力されていません。")
                # 再度ダイアログを表示するか、アプリを終了するかなどのハンドリングも可能
                self.show_api_key_dialog()  # 再度表示する例

    def init_ui(self):
        """UIの初期化"""
        self.setWindowTitle("Google Text-to-Speech GUI")
        self.setGeometry(300, 300, 500, 400)  # ウィンドウサイズ調整 (少し縦長に)

        layout = QVBoxLayout()

        # --- APIキー設定ボタン ---
        api_key_button = QPushButton("APIキー設定")
        api_key_button.clicked.connect(self.show_api_key_dialog)
        layout.addWidget(api_key_button)  # ボタンをレイアウトに追加

        # --- 入力ファイル ---
        input_layout = QHBoxLayout()
        self.input_label = QLabel("入力テキストファイル:")
        self.input_path_display = QLineEdit()
        self.input_path_display.setReadOnly(True)
        input_button = QPushButton("選択...")
        input_button.clicked.connect(self.select_input_file)
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_path_display)
        input_layout.addWidget(input_button)
        layout.addLayout(input_layout)

        # --- 出力先 ---
        output_layout = QHBoxLayout()
        self.output_label = QLabel("MP3保存先ディレクトリ:")
        self.output_path_display = QLineEdit(self.output_dir_path)  # 初期値を表示
        self.output_path_display.setReadOnly(True)
        output_button = QPushButton("選択...")
        output_button.clicked.connect(self.select_output_dir)
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_path_display)
        output_layout.addWidget(output_button)
        layout.addLayout(output_layout)

        # --- 再生速度 ---
        speed_layout = QHBoxLayout()
        self.speed_label = QLabel("再生速度 (x1.0):")
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(25)  # 0.25倍速
        self.speed_slider.setMaximum(400)  # 4.0倍速
        self.speed_slider.setValue(100)  # デフォルト1.0倍速
        self.speed_slider.setTickInterval(25)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.valueChanged.connect(self.update_speed_label)

        self.speed_spinbox = QSpinBox()  # 値表示用、直接編集は非推奨
        self.speed_spinbox.setMinimum(25)
        self.speed_spinbox.setMaximum(400)
        self.speed_spinbox.setValue(100)
        self.speed_spinbox.setSuffix("%")
        self.speed_spinbox.valueChanged.connect(self.update_slider_value)
        self.speed_spinbox.setReadOnly(True)  # スライダーと連動させるためReadOnlyに

        speed_layout.addWidget(self.speed_label)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_spinbox)  # スピンボックスも追加
        layout.addLayout(speed_layout)

        # --- 実行ボタン ---
        self.convert_button = QPushButton("音声ファイル作成")
        self.convert_button.clicked.connect(self.start_conversion)
        layout.addWidget(self.convert_button)

        # --- 再生ボタン ---
        self.play_button = QPushButton("再生")
        self.play_button.clicked.connect(self.play_last_audio)
        self.play_button.setEnabled(False)  # 初期状態は無効
        layout.addWidget(self.play_button)

        # --- ステータスラベル ---
        self.status_label = QLabel("準備完了")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def update_speed_label(self, value):
        """スライダーの値が変更されたらラベルとスピンボックスを更新"""
        speed = value / 100.0
        self.speed_label.setText(f"再生速度 (x{speed:.2f}):")
        # スライダーとスピンボックスの相互更新ループを防ぐ
        if self.speed_spinbox.value() != value:
            self.speed_spinbox.setValue(value)

    def update_slider_value(self, value):
        """スピンボックスの値が変更されたらスライダーを更新"""
        # スライダーとスピンボックスの相互更新ループを防ぐ
        if self.speed_slider.value() != value:
            self.speed_slider.setValue(value)

    def select_input_file(self):
        """入力テキストファイルを選択するダイアログを表示"""
        # 柔軟なファイル形式に対応するため、フィルタを設定
        filter_str = (
            "テキストファイル (*.txt *.md *.rtf *.html *.xml);;すべてのファイル (*)"
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self, "入力テキストファイルを選択", "", filter_str
        )
        if file_path:
            self.input_file_path = file_path
            self.input_path_display.setText(file_path)
            self.status_label.setText("ファイルを選択しました。")

    def select_output_dir(self):
        """出力先ディレクトリを選択するダイアログを表示"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "保存先ディレクトリを選択", self.output_dir_path
        )
        if dir_path:
            self.output_dir_path = dir_path
            self.output_path_display.setText(dir_path)
            self.status_label.setText("保存先を選択しました。")

    def start_conversion(self):
        """音声変換処理を開始"""
        # 再生ボタンを無効化
        self.play_button.setEnabled(False)

        # --- APIキーチェック --- 開始
        # APIキーが設定されているか確認
        if not self.api_key:
            # .envファイルから読み込み試行
            self.load_api_key()
            # それでもなければダイアログ表示
            if not self.api_key:
                self.show_api_key_dialog()
                # ダイアログ後もAPIキーがなければ処理中断
                if not self.api_key:
                    QMessageBox.warning(
                        self,
                        "APIキー未設定",
                        "APIキーが設定されていません。処理を中止します。",
                    )
                    return  # 処理を中断
        # --- APIキーチェック --- 終了

        # --- 入力テキストの取得と検証 ---
        if not self.input_file_path:
            QMessageBox.warning(
                self, "エラー", "入力テキストファイルを選択してください。"
            )
            return

        if not self.output_dir_path:
            QMessageBox.warning(
                self, "エラー", "保存先ディレクトリを選択してください。"
            )
            return

        try:
            with open(self.input_file_path, "r", encoding="utf-8") as f:
                input_text = f.read()
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"ファイル読み込みエラー: {e}")
            return

        if not input_text.strip():
            QMessageBox.warning(self, "エラー", "入力テキストが空です。")
            return

        # 出力ファイルパスを生成 (入力ファイル名 + .mp3)
        input_filename = Path(self.input_file_path).stem
        output_filename = f"{input_filename}.mp3"
        output_path = Path(self.output_dir_path) / output_filename

        self.status_label.setText("変換中...")
        self.convert_button.setEnabled(False)  # 変換中はボタンを無効化

        # スレッドで変換を実行
        self.conversion_thread = ConversionThread(
            api_key=self.api_key,
            text=input_text,
            output_path=str(output_path),
            speaking_rate=self.speed_slider.value() / 100.0,
        )
        self.conversion_thread.conversion_finished.connect(self.on_conversion_finished)
        self.conversion_thread.conversion_error.connect(self.on_conversion_error)
        self.conversion_thread.start()

    def on_conversion_finished(self, file_path, message):
        """変換成功時の処理"""
        QMessageBox.information(self, "完了", message)
        self.status_label.setText("変換完了")
        self.convert_button.setEnabled(True)  # ボタンを再度有効化
        self.last_output_path = file_path  # 最後に生成したファイルのパスを保持
        self.play_button.setEnabled(True)  # 再生ボタンを有効化

    def on_conversion_error(self, error_message):
        """変換失敗時の処理"""
        QMessageBox.critical(self, "変換エラー", error_message)
        self.status_label.setText(f"エラー: {error_message}")
        self.convert_button.setEnabled(True)  # ボタンを再度有効化

    def play_last_audio(self):
        """最後に生成した音声ファイルを再生"""
        if self.last_output_path:
            try:
                # macOSの場合 'open' コマンドを使用
                if sys.platform == "darwin":
                    subprocess.run(["open", self.last_output_path], check=True)
                # Windowsの場合
                elif os.name == "nt":
                    os.startfile(self.last_output_path)
                # Linuxの場合
                elif sys.platform.startswith("linux"):
                    subprocess.run(["xdg-open", self.last_output_path], check=True)
                else:
                    QMessageBox.warning(
                        self, "非対応OS", "このOSでの自動再生はサポートされていません。"
                    )
            except FileNotFoundError:
                QMessageBox.critical(
                    self, "エラー", f"ファイルが見つかりません: {self.last_output_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "エラー", f"音声ファイルの再生に失敗しました: {e}"
                )
        else:
            QMessageBox.warning(self, "警告", "音声ファイルが生成されていません。")

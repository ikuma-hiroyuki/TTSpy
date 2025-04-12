from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import GoogleAPICallError, ClientError
from google.cloud import texttospeech


# --- Text-to-Speech処理用スレッド ---
class ConversionThread(QThread):
    """Text-to-Speech変換をバックグラウンドで実行するスレッド"""

    conversion_finished = pyqtSignal(
        str, str
    )  # ファイルパス(str)とメッセージ(str)を送信
    conversion_error = pyqtSignal(str)

    def __init__(self, api_key, text, output_path, speaking_rate, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.text = text
        self.output_path = output_path
        self.speaking_rate = speaking_rate

    def run(self):
        """Text-to-Speech変換を実行"""
        try:
            if not self.api_key:
                raise ValueError("APIキーが設定されていません。")
            if not self.text:
                raise ValueError("入力テキストが空です。")
            if not self.output_path:
                raise ValueError("出力先が指定されていません。")

            # APIキーを使用してクライアントオプションを設定
            client_options = ClientOptions(api_key=self.api_key)
            client = texttospeech.TextToSpeechClient(client_options=client_options)

            synthesis_input = texttospeech.SynthesisInput(text=self.text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="ja-JP", name="ja-JP-Neural2-B"  # 必要に応じて変更可能
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=self.speaking_rate,
            )

            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            # 出力ディレクトリが存在しない場合は作成
            Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)

            with open(self.output_path, "wb") as out:
                out.write(response.audio_content)

            self.conversion_finished.emit(
                self.output_path,
                f'音声ファイルが "{self.output_path}" に保存されました。',
            )

        except (GoogleAPICallError, ClientError, ValueError, FileNotFoundError) as e:
            self.conversion_error.emit(f"エラーが発生しました: {e}")
        except Exception as e:  # その他の予期せぬエラー
            self.conversion_error.emit(f"予期せぬエラーが発生しました: {e}")

import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt
import os
import subprocess

class DragDropWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setWindowTitle("MP4ファイル結合アプリ")
        self.resize(400, 300)
        self.files = []

        layout = QVBoxLayout()
        self.label = QLabel("ここにMP4ファイルをドラッグ＆ドロップしてください")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        self.merge_button = QPushButton("結合して保存")
        self.merge_button.clicked.connect(self.merge_files)
        self.merge_button.setEnabled(False)
        layout.addWidget(self.merge_button)

        self.setLayout(layout)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        self.files = [url.toLocalFile() for url in urls if url.toLocalFile().lower().endswith('.mp4')]
        if self.files:
            self.label.setText('\n'.join(os.path.basename(f) for f in self.files))
            self.merge_button.setEnabled(True)
        else:
            self.label.setText("MP4ファイルのみ対応しています")
            self.merge_button.setEnabled(False)

    def merge_files(self):
        if not self.files:
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "保存先を選択", "", "MP4 Files (*.mp4)")
        if not save_path:
            return

        # 一時ファイルリスト作成
        list_file = "filelist.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for file in self.files:
                f.write(f"file '{file.replace('\'', '\\\'')}'\n")

        # ffmpegで結合
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            save_path
        ]
        try:
            subprocess.run(cmd, check=True)
            QMessageBox.information(self, "完了", "ファイルの結合が完了しました。")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"結合に失敗しました: {e}")
        finally:
            if os.path.exists(list_file):
                os.remove(list_file)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DragDropWidget()
    window.show()
    sys.exit(app.exec())
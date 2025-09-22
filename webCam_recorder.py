import os
import time
import datetime
from PyQt6.QtCore import QSize, pyqtSignal, pyqtSlot, QThread
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QFileDialog)
from PyQt6.QtGui import QImage, QPixmap
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont


# フォントのパス（システムに応じて変更してください）
FONT_PATH = f"Fonts/msgothic.ttc"


class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    playing = True

    def run(self):
        cap = cv2.VideoCapture(0)
        while self.playing:
            ret, frame = cap.read()
            if ret:
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
                self.change_pixmap_signal.emit(image)
        cap.release()
    
    def stop(self):
        self.playing = False
        self.wait()

class Window(QWidget):

    video_size = QSize(1280, 720)

    def __init__(self, fps=10, section_time=60, camera_pixel=[1280, 720]):
        super().__init__()
        self.initUI()
        self.thread = VideoThread()
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.start()
        self._run_flag = True
        self.fps = fps
        self.section_time = section_time
        self.camera_pixel = camera_pixel
    
    def initUI(self):
        self.setWindowTitle("WebCam Recorder")
        self.image_label = QLabel(self)
        self.image_label.resize(self.video_size)
        self.btn_start = QPushButton("Start Recording")
        self.btn_start.clicked.connect(self.start_recording)
        self.btn_stop = QPushButton("Stop Recording")
        self.btn_stop.clicked.connect(self.stop_recording)
        vbox = QVBoxLayout()
        vbox.addWidget(self.image_label)
        vbox.addWidget(self.btn_start)
        vbox.addWidget(self.btn_stop)
        self.setLayout(vbox)
        self.resize(self.video_size.width(), self.video_size.height() + 100)
        self.show()

    def closeEvent(self, event):
        self.thread.stop()
        event.accept()
    
    @pyqtSlot(QImage)
    def update_image(self, cv_img):
        self.image_label.setPixmap(QPixmap.fromImage(cv_img).scaled(self.video_size))

    def start_recording(self):
        print("Start Recording")

    def stop_recording(self):
        print("Stop Recording")


def capture_time_lapse(output_dir, fps=10, section_time=60, camera_pixel=[1280, 720]):
    # Webカメラを開く
    cap = cv2.VideoCapture(0)
    # カメラの解像度を設定
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_pixel[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_pixel[1])

    # 設定が反映されたか確認
    actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"カメラ解像度: {actual_width}x{actual_height}")

    if not cap.isOpened():
        print("カメラを開けません")
        return
    os.makedirs(output_dir, exist_ok=True)
    
    file_no = 1
    section_start_time = time.time()

    interval = 1.0 / fps  # キャプチャ間隔（秒）
    last_capture_time = time.time()

    # 録画ファイルの設定
    output_file = f"video_{file_no}.mp4"
    outputpath = os.path.join(output_dir, output_file)
    fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v') # MJPEGコーデック
    video = cv2.VideoWriter(outputpath, fourcc, fps, (int(cap.get(3)), int(cap.get(4))))
    print(f"画像サイズ: {int(cap.get(3))}x{int(cap.get(4))}, FPS: {fps}")

    # 映像を取得する
    while True:
        now = time.time()
        # 一定時間経過したら新しいファイルに切り替え
        if now - section_start_time >= section_time*60:
            video.release()  # 現在の録画ファイルを閉じる
            file_no += 1
            section_start_time = now
            output_file = f"video_{file_no}.mp4"
            outputpath = os.path.join(output_dir, output_file)
            video = cv2.VideoWriter(outputpath, fourcc, fps, (int(cap.get(3)), int(cap.get(4))))
            print(f"新しい録画ファイルに切り替え: {outputpath}")
        else:
            # 一定間隔でフレームをキャプチャ
            if now - last_capture_time >= interval:
                time_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 現在の日時を取得
                ret, frame = cap.read()  # フレームを読み込む
                if not ret:
                    break
                
                # OpenCVの画像をPillow形式に変換
                frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                # Pillowで日時を描画
                draw = ImageDraw.Draw(frame_pil)
                font = ImageFont.truetype(FONT_PATH, 32)  # フォントサイズを指定
                draw.text((10, 10), time_stamp, font=font, fill=(255, 255, 255))  # 白色で描画
                # Pillowの画像をOpenCV形式に戻す
                frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)

                video.write(frame)  # フレームを録画ファイルに書き込む
                last_capture_time = now

            else:
                continue
        if cv2.waitKey(1) & 0xFF == ord('q'):  # 'q'キーで終了
            break
        cv2.imshow('Recording...', frame)  # 映像を表示する

    cap.release()  # カメラを解放
    cv2.destroyAllWindows()  # ウィンドウを閉じる
    print(f"録画が完了しました: {outputpath}")

def main():
    output_dir = "time_lapse_videos"
    # 解像度を設定（幅と高さ）
    camera_pixel = [1280, 720]  # 幅x高さ
    fps = 10
    section_time = 60  # 指定時間間隔ごとに新しいフォルダに保存(単位:分)
    # capture_time_lapse(output_dir, fps, section_time, camera_pixel)
    app = QApplication([])
    window = Window(fps, section_time, camera_pixel)
    window.show()
    app.exec()



if __name__ == "__main__":
    main()
import sys

from PyQt6 import QtGui
from PyQt6.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout,QHBoxLayout, QMainWindow, QComboBox, QPushButton, QSizePolicy
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPixmap, QImage


from PyQt6.QtCore import pyqtSignal, pyqtSlot, QThread

import cv2
import numpy as np

# class VideoThread(QThread):
#     # シグナル設定
#     change_pixmap_signal = pyqtSignal(np.ndarray)

#     def __init__(self):
#         super().__init__()
#         self._run_flag = True

#     # QThreadのrunメソッドを定義
#     def run(self):
#         cap = cv2.VideoCapture(0)
#         while self._run_flag:
#             ret, cv_img = cap.read() # 1フレーム取得
#             # 新たなフレームを取得できたら
#             # シグナル発信(cv_imgオブジェクトを発信)            
#             if ret:
#                 self.change_pixmap_signal.emit(cv_img)

#         # videoCaptureのリリース処理
#         cap.release()
   
#     # スレッドが終了するまでwaitをかける
#     def stop(self):
#         self._run_flag = False
#         self.wait()


# class App(QWidget):

#     def __init__(self):
#         super().__init__()

#         self.image_label = QLabel(self)
        
#         # vboxにQLabelをセット
#         vbox = QVBoxLayout()
#         vbox.addWidget(self.image_label)

#         # vboxをレイアウトとして配置
#         self.setLayout(vbox)

#         # ビデオキャプチャ用のスレッドオブジェクトを生成
#         self.thread = VideoThread()
#         # ビデオスレッド内のchange_pixmap_signalオブジェクトのシグナルに対するslot
#         self.thread.change_pixmap_signal.connect(self.update_image)

#         self.thread.start() # スレッドを起動

#     def get_available_cameras(self):
#             """利用可能なカメラを検出"""
#             cameras = []
#             for i in range(10):  # 最大10台までチェック
#                 cap = cv2.VideoCapture(i)
#                 if cap.isOpened():
#                     cameras.append(f"カメラ {i}")
#                     cap.release()
#             return cameras
    



#     # 終了時にスレッドがシングルになるようにする
#     def closeEvent(self,event):
#         self.thread.stop()
#         event.accept()


#     @pyqtSlot(np.ndarray)
#     def update_image(self, cv_img):
#         #img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
#         # QT側でチャネル順BGRを指定
#         qimg = QtGui.QImage(cv_img.tobytes(),cv_img.shape[1],cv_img.shape[0],cv_img.strides[0],QtGui.QImage.Format.Format_BGR888)
#         qpix = QPixmap.fromImage(qimg)
#         self.image_label.setPixmap(qpix)

# if __name__ == "__main__":
#    app = QApplication([])
#    window = App()
#    window.show()
#    app.exec()

class CameraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("アプリ")
        self.setGeometry(100, 100, 800, 600)

        # メインウィジェットとレイアウト
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.v_layout = QVBoxLayout(self.central_widget)

        # 1行目の水平レイアウト
        self.horizontalLayout_1 = QHBoxLayout()
        self.horizontalLayout_1.setObjectName("horizontalLayout_1")
        # カメラ選択用のコンボボックス
        self.camera_selector = QComboBox()
        self.horizontalLayout_1.addWidget(self.camera_selector)
        # 開始ボタン
        self.connect_camera_button = QPushButton("カメラ接続")
        self.horizontalLayout_1.addWidget(self.connect_camera_button)
        self.v_layout.addLayout(self.horizontalLayout_1)
        # self.horizontalLayout_1.addWidget(self.start_button)
        # カメラ映像表示用ラベル
        self.video_label = QLabel()
        self.v_layout.addWidget(self.video_label)
        self.video_label.setFixedSize(640, 480)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setText("カメラ映像")
        self.video_label.setObjectName("video_label")
        self.video_label.setScaledContents(True)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        # 録画開始ボタン
        self.record_start_button = QPushButton("録画開始")
        self.record_start_button.setObjectName("record_start_button")
        self.v_layout.addWidget(self.record_start_button)
        self.record_start_button.setEnabled(False)  # 録画ボタンは初期状態で無効

        # 録画停止ボタン
        self.record_stop_button = QPushButton("録画停止")
        self.record_stop_button.setObjectName("record_stop_button")
        self.v_layout.addWidget(self.record_stop_button)
        self.record_stop_button.setEnabled(False)  # 停止ボタンは初期状態で無効

        # カメラリストを取得
        self.available_cameras = self.get_available_cameras()
        self.camera_selector.addItems(self.available_cameras)

        # OpenCV関連
        self.capture = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        self.recording = False  # 録画状態フラグ
        self.video_writer = None  # 動画ライターオブジェクト

        # イベント接続
        self.connect_camera_button.clicked.connect(self.start_camera)
        self.record_start_button.clicked.connect(self.record_video)
        self.record_stop_button.clicked.connect(self.stop_recording)

    def get_available_cameras(self):
        """利用可能なカメラを検出"""
        cameras = []
        for i in range(10):  # 最大10台までチェック
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cameras.append(f"カメラ {i}")
                cap.release()
        return cameras

    def start_camera(self):
        """選択したカメラを開始"""
        camera_index = self.camera_selector.currentIndex()
        if self.capture:
            self.capture.release()
        self.capture = cv2.VideoCapture(camera_index)
        self.timer.start(30)  # 30msごとにフレーム更新

    def update_frame(self):
        """カメラフレームを更新"""
        ret, frame = self.capture.read()
        if ret:
            # OpenCVのBGR画像をRGBに変換
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = frame.shape
            step = channel * width
            q_image = QImage(frame.data, width, height, step, QImage.Format.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(q_image))

    def record_video(self):
        
        print("recording...")
    
    def stop_recording(self):
        print("stopped.")

    def closeEvent(self, event):
        """アプリ終了時にリソースを解放"""
        if self.capture:
            self.capture.release()
        self.timer.stop()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CameraApp()
    window.show()
    sys.exit(app.exec())
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QGridLayout
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer
import cv2
from collections import deque
from threading import Thread
import time
from roi_utils import fetch_all_rois, draw_rois
from thermal_receiver import ThermalReceiver
from PyQt5 import uic

DELAY_SEC = 1
DEFAULT_IP   = "192.168.0.56"
DEFAULT_PORT = "554"
THERMAL_PORT = 60110

class FrameReader(Thread):
    def __init__(self, url, delay_sec):
        super().__init__(daemon=True)
        self.url = url
        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.delay_frames = int(delay_sec * fps)
        self.frames = deque(maxlen=self.delay_frames + 1)
        self.running = True

    def run(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frames.append(frame)
            else:
                time.sleep(0.01)

    def get_delayed(self):
        if len(self.frames) == self.frames.maxlen:
            return self.frames[0]
        return None

    def stop(self):
        self.running = False
        self.cap.release()


class OpenCVViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("viewer.ui", self)

        # 내부 상태 초기화
        self.reader = None
        self.receiver = None
        self.thermal_data = {}  # area_id -> {max, min, avr}
        self.rois = []
        self.resolution_shown = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.roi_label_matrix = []

        # 버튼 연결
        self.start_button.clicked.connect(self.start_stream)
        self.stop_button.clicked.connect(self.stop_stream)

        # ROI 라벨 테이블 구성
        grid_layout = self.roi_grid.layout()

        # 🔼 헤더 추가
        grid_layout.addWidget(QLabel("영역"), 0, 0)
        grid_layout.addWidget(QLabel("Max"), 0, 1)
        grid_layout.addWidget(QLabel("Min"), 0, 2)
        grid_layout.addWidget(QLabel("Avg"), 0, 3)

        for i in range(10):
            max_lbl = QLabel("-")
            min_lbl = QLabel("-")
            avr_lbl = QLabel("-")
            grid_layout.addWidget(QLabel(f"ROI{i}"), i + 1, 0)
            grid_layout.addWidget(max_lbl, i + 1, 1)
            grid_layout.addWidget(min_lbl, i + 1, 2)
            grid_layout.addWidget(avr_lbl, i + 1, 3)
            self.roi_label_matrix.append({
                "max": max_lbl,
                "min": min_lbl,
                "avr": avr_lbl
            })

    def start_stream(self):
        ip = self.ip_input.text().strip()
        port = self.port_input.text().strip()
        rtsp_url = f"rtsp://{ip}:{port}/stream1"

        self.stop_stream()
        self.reader = FrameReader(rtsp_url, DELAY_SEC)
        self.reader.start()
        self.timer.start(33)
        self.resolution_label.setText("해상도: -")
        self.resolution_shown = False
        self.rois = fetch_all_rois(ip)

        self.receiver = ThermalReceiver(ip, THERMAL_PORT, self.thermal_data)
        self.receiver.start()

        QTimer.singleShot(5000, self.check_stream_timeout)

    def check_stream_timeout(self):
        if self.reader and not self.reader.cap.isOpened():
            self.stop_stream()

    def stop_stream(self):
        if self.reader:
            self.timer.stop()
            self.reader.stop()
            self.reader.join()
            self.reader = None
        if self.receiver:
            self.receiver.stop()
            self.receiver = None
        self.video_label.clear()
        self.resolution_label.setText("해상도: -")

    def update_frame(self):
        if self.reader:
            frame = self.reader.get_delayed()
            if frame is not None:
                original_h, original_w = frame.shape[:2]

                if not self.resolution_shown:
                    self.resolution_label.setText(f"해상도: {original_w}×{original_h}")
                    self.resolution_shown = True

                if (original_w, original_h) != (640, 480):
                    resized_w, resized_h = 640, 480
                    scale_x = resized_w / original_w
                    scale_y = resized_h / original_h
                    frame = cv2.resize(frame, (resized_w, resized_h))
                else:
                    scale_x = scale_y = 1.0

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                if self.rois:
                    draw_rois(rgb, self.rois, self.thermal_data, scale_x, scale_y)

                for i in range(10):
                    temp = self.thermal_data.get(i)
                    if temp:
                        self.roi_label_matrix[i]["max"].setText(f"{temp['max']}℃")
                        self.roi_label_matrix[i]["min"].setText(f"{temp['min']}℃")
                        self.roi_label_matrix[i]["avr"].setText(f"{temp['avr']}℃")
                    else:
                        self.roi_label_matrix[i]["max"].setText("-")
                        self.roi_label_matrix[i]["min"].setText("-")
                        self.roi_label_matrix[i]["avr"].setText("-")

                h, w, ch = rgb.shape
                qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
                self.video_label.setPixmap(QPixmap.fromImage(qimg))

    def closeEvent(self, event):
        self.stop_stream()
        super().closeEvent(event)
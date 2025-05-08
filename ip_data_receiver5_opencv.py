import sys
import cv2
import time
import requests
import json
import re
import os
from collections import deque
from threading import Thread

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit, QPushButton,QVBoxLayout,QGridLayout,
    QVBoxLayout, QHBoxLayout, QWidget
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer


DELAY_SEC = 1
DEFAULT_IP   = "192.168.0.56"
DEFAULT_PORT = "554"


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


def fetch_all_rois(ip):
    rois = []
    try:
        for i in range(10):
            url = f"http://{ip}/cgi-bin/control/camthermalroi.cgi"
            params = {
                "id": "admin",
                "passwd": "admin",
                "action": f"getthermalroi{i}"
            }
            resp = requests.get(url, params=params, timeout=2)
            if resp.status_code == 200:
                lines = resp.text.strip().splitlines()
                data = {
                    k.strip(): v.strip()
                    for line in lines if "=" in line
                    for k, v in [line.split("=", 1)]
                }
                if data.get("roi_use") == "on":
                    try:
                        sx = int(data["startx"])
                        sy = int(data["starty"])
                        ex = int(data["endx"])
                        ey = int(data["endy"])
                        rois.append((sx, sy, ex, ey))
                    except Exception:
                        continue
    except Exception:
        pass
    return rois


def draw_rois(frame, rois):
    for sx, sy, ex, ey in rois:
        cv2.rectangle(frame, (sx, sy), (ex, ey), (0, 0, 255), 2)


def load_latest_roi_temps(file_path='thermal_camera_data.txt'):
    results = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        matches = re.findall(r'\[\s*{.*?}\s*\]', content, re.DOTALL)
        if not matches:
            return results
        last_block = matches[-1]
        data_list = json.loads(last_block)
        for entry in data_list:
            area_id = entry.get("area_id")
            if area_id is not None:
                results[area_id] = {
                    "max": entry.get("temp_max", "-"),
                    "min": entry.get("temp_min", "-"),
                    "avr": entry.get("temp_avr", "-")
                }
    except Exception:
        pass
    return results

class OpenCVViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RTSP Viewer (OpenCV + ROI + Temp Table)")
        self.setGeometry(100, 100, 1000, 700)

        self.video_label = QLabel(self)
        self.video_label.setFixedSize(640, 480)

        self.resolution_label = QLabel("해상도: -")
        self.resolution_label.setFixedWidth(180)
        self.resolution_label.setStyleSheet("font-size: 14px;")

        self.ip_input = QLineEdit(DEFAULT_IP)
        self.port_input = QLineEdit(DEFAULT_PORT)
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")

        self.start_button.clicked.connect(self.start_stream)
        self.stop_button.clicked.connect(self.stop_stream)

        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("IP:"))
        control_layout.addWidget(self.ip_input)
        control_layout.addWidget(QLabel("Port:"))
        control_layout.addWidget(self.port_input)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)

        video_layout = QHBoxLayout()
        video_layout.addWidget(self.video_label)

        # ───── 우측 정보 패널 구성 (해상도 + 온도표)
        side_layout = QVBoxLayout()
        side_layout.addWidget(self.resolution_label)

        # 표 형태로 ROI 온도 정보 배치
        self.roi_label_matrix = []
        roi_grid = QGridLayout()
        roi_grid.addWidget(QLabel(""), 0, 0)
        roi_grid.addWidget(QLabel("최대"), 0, 1)
        roi_grid.addWidget(QLabel("최소"), 0, 2)
        roi_grid.addWidget(QLabel("평균"), 0, 3)

        for i in range(10):
            roi_grid.addWidget(QLabel(f"ROI{i}"), i + 1, 0)
            row_labels = {
                "max": QLabel("-"),
                "min": QLabel("-"),
                "avr": QLabel("-")
            }
            roi_grid.addWidget(row_labels["max"], i + 1, 1)
            roi_grid.addWidget(row_labels["min"], i + 1, 2)
            roi_grid.addWidget(row_labels["avr"], i + 1, 3)
            self.roi_label_matrix.append(row_labels)

        side_layout.addLayout(roi_grid)
        video_layout.addLayout(side_layout)

        # 전체 레이아웃 정리
        layout = QVBoxLayout()
        layout.addLayout(control_layout)
        layout.addLayout(video_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.reader = None
        self.resolution_shown = False
        self.rois = []

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
        self.video_label.clear()
        self.resolution_label.setText("해상도: -")

    def update_frame(self):
        if self.reader:
            frame = self.reader.get_delayed()
            if frame is not None:
                if not self.resolution_shown:
                    h, w = frame.shape[:2]
                    self.resolution_label.setText(f"해상도: {w}×{h}")
                    self.resolution_shown = True

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                if self.rois:
                    draw_rois(rgb, self.rois)

                # ROI 온도 데이터 갱신
                temps = load_latest_roi_temps()
                for i in range(10):
                    temp = temps.get(i)
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



if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = OpenCVViewer()
    viewer.show()
    sys.exit(app.exec_())

from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QGridLayout, QMessageBox
)
from PyQt5.QtGui import QImage, QPixmap, QColor
from PyQt5.QtCore import QTimer
import cv2
from collections import deque
from threading import Thread
import time
import os
import sys
from roi_utils import fetch_all_rois, draw_rois
from thermal_receiver import ThermalReceiver
from alarm_utils import fetch_alarm_conditions  # 🔔 알람 조건 가져오기
from PyQt5 import uic
from ip_selector_popup import IPSelectorPopup
from graph_viewer import GraphWindow
from Camera_Control.image import ImageControlPopup
from Camera_Control.display import DisplayControlPopup
from Camera_Control.enhancement import EnhancementControlPopup
from Camera_Control.correction import CorrectionControlPopup
from Camera_Control.nuc import NUCControlPopup


DELAY_SEC = 1
DEFAULT_IP   = "192.168.0.56"
DEFAULT_PORT = "554"
THERMAL_PORT = 60110

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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
            if not self.cap.isOpened():
                break
            ret, frame = self.cap.read()
            if not self.running:
                break
            if ret:
                self.frames.append(frame)
            else:
                time.sleep(0.01)

        if self.cap.isOpened():
            self.cap.release()

    def get_delayed(self):
        if not self.running or not self.cap.isOpened():
            return None
        if len(self.frames) == self.frames.maxlen:
            return self.frames[0]
        return None

    def stop(self):
        self.running = False


class OpenCVViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path("viewer.ui"), self)

        self.reader = None
        self.receiver = None
        self.thermal_data = {}
        self.rois = []
        self.roi_alarm_config = []  # 🔔 알람 조건 저장용
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.roi_label_matrix = []
        self.graph_window = None

        self.start_button.clicked.connect(self.start_stream)
        self.stop_button.clicked.connect(self.stop_stream)
        self.search_button.clicked.connect(self.open_ip_selector)
        self.time_plot_button.clicked.connect(self.open_graph_viewer)
        self.actionImage.triggered.connect(self.open_image_control_popup)
        self.actionDisplay.triggered.connect(self.open_display_control_popup)
        self.actionEnhancement.triggered.connect(self.open_enhancement_control_popup)
        self.actionCorrection.triggered.connect(self.open_correction_control_popup)
        self.actionNUC.triggered.connect(self.open_nuc_control_popup)

        self.update_button_states(False)

        grid_layout = self.roi_grid.layout()
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
            self.roi_label_matrix.append({"max": max_lbl, "min": min_lbl, "avr": avr_lbl})

    def open_nuc_control_popup(self):
        ip = self.ip_input.text().strip()
        user_id = self.id_input.text().strip()
        user_pw = self.pw_input.text().strip()

        if not ip or not user_id or not user_pw:
            QMessageBox.warning(self, "입력 오류", "IP, ID, PW를 모두 입력하세요.")
            return

        self.nuc_popup = NUCControlPopup(ip, user_id, user_pw, self)
        self.nuc_popup.show()

    def open_correction_control_popup(self):
        ip = self.ip_input.text().strip()
        user_id = self.id_input.text().strip()
        user_pw = self.pw_input.text().strip()

        if not ip or not user_id or not user_pw:
            QMessageBox.warning(self, "입력 오류", "IP, ID, PW를 모두 입력하세요.")
            return

        self.correction_popup = CorrectionControlPopup(ip, user_id, user_pw, self)
        self.correction_popup.show()

    def open_enhancement_control_popup(self):
        ip = self.ip_input.text().strip()
        user_id = self.id_input.text().strip()
        user_pw = self.pw_input.text().strip()

        if not ip or not user_id or not user_pw:
            QMessageBox.warning(self, "입력 오류", "IP, ID, PW를 모두 입력하세요.")
            return

        self.enhancement_popup = EnhancementControlPopup(ip, user_id, user_pw, self)
        self.enhancement_popup.show()

    def open_image_control_popup(self):
        ip = self.ip_input.text().strip()
        user_id = self.id_input.text().strip()
        user_pw = self.pw_input.text().strip()

        if not ip or not user_id or not user_pw:
            QMessageBox.warning(self, "입력 오류", "IP, ID, PW를 모두 입력하세요.")
            return

        self.image_popup = ImageControlPopup(ip, user_id, user_pw, self)
        self.image_popup.show()

    def open_display_control_popup(self):
        ip = self.ip_input.text().strip()
        user_id = self.id_input.text().strip()
        user_pw = self.pw_input.text().strip()

        if not ip or not user_id or not user_pw:
            QMessageBox.warning(self, "입력 오류", "IP, ID, PW를 모두 입력하세요.")
            return

        self.display_popup = DisplayControlPopup(ip, user_id, user_pw, self)
        self.display_popup.show()

    def update_button_states(self, connected):
        self.start_button.setEnabled(not connected)
        self.search_button.setEnabled(not connected)
        self.ip_input.setEnabled(not connected)
        self.id_input.setEnabled(not connected)
        self.pw_input.setEnabled(not connected)

        self.stop_button.setEnabled(connected)
        self.time_plot_button.setEnabled(connected)

        disabled_style = "background-color: lightgray; color: gray;"
        enabled_style = ""

        for widget in [self.start_button, self.search_button, self.ip_input, self.id_input, self.pw_input]:
            widget.setStyleSheet(enabled_style if widget.isEnabled() else disabled_style)
        for widget in [self.stop_button, self.time_plot_button]:
            widget.setStyleSheet(enabled_style if widget.isEnabled() else disabled_style)

    def open_ip_selector(self):
        popup = IPSelectorPopup(self)
        if popup.exec_() == popup.Accepted:
            selected_ip = popup.get_selected_ip()
            if selected_ip:
                self.ip_input.setText(selected_ip)

    def refresh_rois(self):
        ip = self.ip_input.text().strip()
        user_id = self.id_input.text().strip()
        user_pw = self.pw_input.text().strip()
        self.rois = fetch_all_rois(ip, user_id, user_pw)
        self.roi_alarm_config = fetch_alarm_conditions(ip, user_id, user_pw)  # 🔔 ROI 갱신 시 알람 조건도 다시 가져옴
        print("[OpenCVViewer] ROI 갱신됨")

    def start_stream(self):
        ip = self.ip_input.text().strip()
        port = 554

        user_id = self.id_input.text().strip()
        user_pw = self.pw_input.text().strip()

        self.rois = fetch_all_rois(ip, user_id, user_pw)
        self.roi_alarm_config = fetch_alarm_conditions(ip, user_id, user_pw)
        if self.rois is None:
            QMessageBox.warning(self, "로그인 실패", "ID 또는 비밀번호가 올바르지 않습니다.")
            return

        rtsp_url = f"rtsp://{user_id}:{user_pw}@{ip}:{port}/stream1"

        self.stop_stream()

        self.video_label.setText("연결중...")
        self.video_label.repaint()

        self.reader = FrameReader(rtsp_url, DELAY_SEC)
        self.reader.start()
        self.timer.start(33)

        self.receiver = ThermalReceiver(ip, THERMAL_PORT, self.thermal_data, self.refresh_rois, self.roi_alarm_config)  # 🔔 알람 조건 전달
        self.receiver.start()

        self.update_button_states(True)
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
        self.update_button_states(False)

    def update_frame(self):
        if self.reader:
            frame = self.reader.get_delayed()
            if frame is not None:
                original_h, original_w = frame.shape[:2]

                if (original_w, original_h) != (640, 480):
                    resized_w, resized_h = 640, 480
                    scale_x = resized_w / original_w
                    scale_y = resized_h / original_h
                    frame = cv2.resize(frame, (resized_w, resized_h))
                else:
                    scale_x = scale_y = 1.0

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # ✅ 알람이 발생한 ROI 목록 판단
                alarming_map = {i: [] for i in range(10)}  # {roi_idx: ["max", "min", "avr"]}
                mode_map = {
                    "maximum": "max",
                    "minimum": "min",
                    "average": "avr"
                }

                for i in range(10):
                    roi = self.rois[i] if i < len(self.rois) else None
                    td = self.thermal_data.get(i)
                    if not roi or not td:
                        continue
                    alarm = roi.get("alarm", {})
                    if alarm.get("alarm_use") == "on" and alarm.get("condition") in ("above", "below") and alarm.get("temperature"):
                        try:
                            threshold = float(alarm["temperature"])
                            mode = alarm.get("mode", "maximum")
                            key = mode_map.get(mode)
                            if key and key in td:
                                temp = float(td[key])
                                if (alarm["condition"] == "above" and temp > threshold) or \
                                (alarm["condition"] == "below" and temp < threshold):
                                    alarming_map[i].append(key)
                        except:
                            continue

                if self.rois:
                    draw_rois(rgb, self.rois, self.thermal_data, scale_x, scale_y)

                # ROI 라벨 갱신 + 데이터 표시 강조
                for i in range(10):
                    temp = self.thermal_data.get(i)
                    alerts = alarming_map.get(i, [])
                    if temp:
                        self.roi_label_matrix[i]["max"].setText(f"{temp['max']}℃")
                        self.roi_label_matrix[i]["min"].setText(f"{temp['min']}℃")
                        self.roi_label_matrix[i]["avr"].setText(f"{temp['avr']}℃")
                    else:
                        self.roi_label_matrix[i]["max"].setText("-")
                        self.roi_label_matrix[i]["min"].setText("-")
                        self.roi_label_matrix[i]["avr"].setText("-")

                    self.roi_label_matrix[i]["max"].setStyleSheet("background-color: rgb(255, 128, 128);" if "max" in alerts else "")
                    self.roi_label_matrix[i]["min"].setStyleSheet("background-color: rgb(255, 128, 128);" if "min" in alerts else "")
                    self.roi_label_matrix[i]["avr"].setStyleSheet("background-color: rgb(255, 128, 128);" if "avr" in alerts else "")

                h, w, ch = rgb.shape
                qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
                self.video_label.setPixmap(QPixmap.fromImage(qimg))


    def open_graph_viewer(self):
        ip = self.ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "IP 오류", "IP 주소를 먼저 입력해 주세요.")
            return
        self.graph_window = GraphWindow(ip)
        self.graph_window.show()

    def closeEvent(self, event):
        self.stop_stream()
        if self.graph_window is not None:
            self.graph_window.close()
        super().closeEvent(event)

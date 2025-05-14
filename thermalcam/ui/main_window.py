from PyQt5.QtWidgets import (
    QMainWindow, QLabel,QMessageBox
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer
import cv2
from collections import deque
from threading import Thread
import time
import os
import sys
from PyQt5 import uic
import datetime

from thermalcam.core.roi import fetch_all_rois, draw_rois
from thermalcam.core.alarm import fetch_alarm_conditions
from thermalcam.core.camera_client import ThermalReceiver
from thermalcam.core.focus import FocusController
from thermalcam.core.yolo import YOLODetector

from thermalcam.ui.dialogs.ip_scanner import IPSelectorPopup
from thermalcam.ui.graph_window import GraphWindow
from thermalcam.ui.dialogs.camera_controls.image import ImageControlPopup
from thermalcam.ui.dialogs.camera_controls.display import DisplayControlPopup
from thermalcam.ui.dialogs.camera_controls.enhancement import EnhancementControlPopup
from thermalcam.ui.dialogs.camera_controls.correction import CorrectionControlPopup
from thermalcam.ui.dialogs.camera_controls.nuc import NUCControlPopup
from thermalcam.ui.dialogs.roi_editor import SetROIPopup
import importlib.resources

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
        with importlib.resources.path("thermalcam.resources.ui", "viewer.ui") as ui_file:
            uic.loadUi(str(ui_file), self)

        self.reader = None
        self.receiver = None
        self.thermal_data = {}
        self.rois = []
        self.roi_alarm_config = []  # 🔔 알람 조건 저장용
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.roi_label_matrix = []
        self.graph_window = None
        self.focus_controller = FocusController(
            get_ip_func=lambda: self.ip_input.text().strip(),
            get_speed_func=lambda: self.focusSpeedSlider.value()
        )
        self.focusSpeedSlider.setMinimum(1)
        self.focusSpeedSlider.setMaximum(100)
        self.focusSpeedSlider.setValue(50)

        self.yolo_enabled = False
        self.yolo_detector = None
        self.actionYolo.setCheckable(True)
        self.actionYolo.triggered.connect(self.toggle_yolo_detection)

        self.start_button.clicked.connect(self.start_stream)
        self.stop_button.clicked.connect(self.stop_stream)
        self.search_button.clicked.connect(self.open_ip_selector)
        self.time_plot_button.clicked.connect(self.open_graph_viewer)
        self.actionImage.triggered.connect(self.open_image_control_popup)
        self.actionDisplay.triggered.connect(self.open_display_control_popup)
        self.actionEnhancement.triggered.connect(self.open_enhancement_control_popup)
        self.actionCorrection.triggered.connect(self.open_correction_control_popup)
        self.actionNUC.triggered.connect(self.open_nuc_control_popup)
        self.nuc_button.clicked.connect(self.handle_nuc_once)
        self.actionSet_ROI.triggered.connect(self.open_roi_popup)
        self.focusInButton.pressed.connect(lambda: self.focus_controller.start_focus("in"))
        self.focusInButton.released.connect(self.focus_controller.stop_focus)
        self.focusOutButton.pressed.connect(lambda: self.focus_controller.start_focus("out"))
        self.focusOutButton.released.connect(self.focus_controller.stop_focus)


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

    def open_roi_popup(self):
        ip = self.ip_input.text().strip()
        user_id = self.id_input.text().strip()
        user_pw = self.pw_input.text().strip()

        if not ip or not user_id or not user_pw:
            QMessageBox.warning(self, "입력 오류", "IP, ID, PW를 모두 입력하세요.")
            return

        self.roi_popup = SetROIPopup(ip, user_id, user_pw, self)
        self.roi_popup.show()

    def handle_nuc_once(self):
        pass # TODO: NUC 즉시 실행 기능 추후 구현

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
        self.nuc_button.setEnabled(connected)
        self.focusInButton.setEnabled(connected)
        self.focusOutButton.setEnabled(connected)

        disabled_style = "background-color: lightgray; color: gray;"
        enabled_style = ""

        # for widget in [self.start_button, self.search_button, self.ip_input, self.id_input, self.pw_input]:
        #     widget.setStyleSheet(enabled_style if widget.isEnabled() else disabled_style)
        # for widget in [self.stop_button, self.time_plot_button, self.nuc_button, self.focusInButton, self.focusOutButton]:
        #     widget.setStyleSheet(enabled_style if widget.isEnabled() else disabled_style)

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
            if frame is None:
                return

            original_h, original_w = frame.shape[:2]
            resized = False
            if (original_w, original_h) != (640, 480):
                frame = cv2.resize(frame, (640, 480))
                resized = True

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # ✅ YOLO 적용 및 캡처
            if self.yolo_enabled:
                rgb = self.handle_yolo_detection(rgb)

            # 🔥 ROI + 알람 표시
            scale_x = scale_y = 1.0
            if resized:
                scale_x = 640 / original_w
                scale_y = 480 / original_h

            # draw_rois 포함 기존 알람 처리 및 텍스트 출력 로직 유지
            self.process_roi_display(rgb, scale_x, scale_y)

            # QLabel에 영상 출력
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(qimg))

    def process_roi_display(self, rgb, scale_x, scale_y):
        alarming_map = {i: [] for i in range(10)}
        mode_map = {"maximum": "max", "minimum": "min", "average": "avr"}

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


    def handle_yolo_detection(self, rgb):
        if self.yolo_detector is None:
            self.yolo_detector = YOLODetector()

        boxes, scores = self.yolo_detector.detect(rgb)

        # confidence 0.5 이상인 박스와 점수 필터링
        filtered_boxes = []
        filtered_scores = []
        for box, score in zip(boxes, scores):
            if score >= 0.5:
                filtered_boxes.append(box)
                filtered_scores.append(score)

        if filtered_boxes:
            import numpy as np
            rgb = self.yolo_detector.draw_detections(
                rgb,
                (np.array(filtered_boxes), np.array(filtered_scores))
            )

            now = datetime.datetime.now()
            if not hasattr(self, "last_capture_time"):
                self.last_capture_time = None

            if self.last_capture_time is None or (now - self.last_capture_time).total_seconds() > 2:
                self.save_capture(rgb, now)
                self.last_capture_time = now

        return rgb



    def save_capture(self, rgb, timestamp):
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        capture_dir = os.path.join(desktop_path, "capture")
        os.makedirs(capture_dir, exist_ok=True)

        filename = f"capture_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(capture_dir, filename)

        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        cv2.putText(
            bgr,
            timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            (10, bgr.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5, (0, 255, 255), 1, cv2.LINE_AA
        )
        cv2.imwrite(filepath, bgr)
        print(f"[YOLO 캡처] 저장됨: {filepath}")

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

    def toggle_yolo_detection(self, checked):
        self.yolo_enabled = checked
        if self.yolo_enabled:
            if self.yolo_detector is None:
                self.yolo_detector = YOLODetector()
            QMessageBox.information(self, "YOLO 활성화", "YOLOv8 사람 인식이 활성화되었습니다.")
        else:
            QMessageBox.information(self, "YOLO 비활성화", "YOLOv8 사람이 인식이 비활성화되었습니다.")

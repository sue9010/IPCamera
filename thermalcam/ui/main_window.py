from PyQt5.QtWidgets import (
    QMainWindow,QMessageBox, 
)
from PyQt5.QtCore import QTimer
import os
import sys
from PyQt5 import uic
from PyQt5.QtGui import QTextCursor
from datetime import datetime

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
from thermalcam.ui.roi_display_handler import init_roi_labels
from thermalcam.ui.stream_handler import (
    start_stream, stop_stream, update_frame
)
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QLabel
import os
import time
from PyQt5.QtCore import Qt
from thermalcam.ui.dialogs.email_config import EmailConfigPopup
from thermalcam.core.alarm import evaluate_alarms
from thermalcam.ui.alarm_handlers import show_popup, play_sound, send_email
from thermalcam.core.media_pipe import MediaPipePoseDetector

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


class OpenCVViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        print("[Viewer] UI 파일 로딩 중...")
        with importlib.resources.path("thermalcam.resources.ui", "viewer.ui") as ui_file:
            uic.loadUi(str(ui_file), self)

        print("[Viewer] 기본 속성 초기화")
        self.reader = None
        self.DELAY_SEC = 1
        self.THERMAL_PORT = 60110
        self.stream_start_time = None
        self.receiver = None
        self.thermal_data = {}
        self.rois = []
        self.roi_alarm_config = []  # 🔔 알람 조건 저장용
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: update_frame(self))
        self.roi_label_matrix = []
        self.graph_window = None
        self.focus_controller = FocusController(
            get_ip_func=lambda: self.ip_input.text().strip(),
            get_speed_func=lambda: self.focusSpeedSlider.value()
        )
        self.alarm_settings = {
            "popup": False,
            "sound": False,
            "email": False,
        }
        self.last_alarm_time = 0 
        self.should_draw_rois = False
        self.focusSpeedSlider.setMinimum(1)
        self.focusSpeedSlider.setMaximum(100)
        self.focusSpeedSlider.setValue(50)

        self.yolo_enabled = False
        self.yolo_detector = None
        self.actionYolo.setCheckable(True)
        self.yolo_button.setCheckable(True)

        print("[Viewer] MediaPipe 속성 초기화")
        self.mediapipe_enabled = False
        self.pose_detector = None
        print("[Viewer] 버튼 설정 연결")
        self.mediaPipeButton.setCheckable(True)
        self.mediaPipeButton.clicked.connect(self.toggle_mediapipe_detection)
        print("[Viewer] 나머지 UI 및 연결 초기화 완료")
        self.popupAlarmButton.setCheckable(True)
        self.soundAlarmButton.setCheckable(True)
        self.emailAlarmButton.setCheckable(True)

        self.start_button.clicked.connect(lambda: start_stream(self))
        self.ip_input.returnPressed.connect(lambda: start_stream(self))
        self.stop_button.clicked.connect(lambda: stop_stream(self))
        self.search_button.clicked.connect(self.open_ip_selector)
        self.time_plot_button.clicked.connect(self.open_graph_viewer)
        self.actionImage.triggered.connect(self.open_image_control_popup)
        self.actionDisplay.triggered.connect(self.open_display_control_popup)
        self.actionEnhancement.triggered.connect(self.open_enhancement_control_popup)
        self.actionCorrection.triggered.connect(self.open_correction_control_popup)
        self.actionNUC.triggered.connect(self.open_nuc_control_popup)
        # self.nuc_button.clicked.connect(self.handle_nuc_once)
        self.actionSet_ROI.triggered.connect(self.open_roi_popup)
        self.focusInButton.pressed.connect(lambda: self.focus_controller.start_focus("in"))
        self.focusInButton.released.connect(self.focus_controller.stop_focus)
        self.focusOutButton.pressed.connect(lambda: self.focus_controller.start_focus("out"))
        self.focusOutButton.released.connect(self.focus_controller.stop_focus)
        self.yolo_button.clicked.connect(self.toggle_yolo_detection)
        self.log_console.moveCursor(QTextCursor.End)
        self.popupAlarmButton.clicked.connect(self.toggle_popup_alarm)
        self.soundAlarmButton.clicked.connect(self.toggle_sound_alarm)
        self.emailAlarmButton.clicked.connect(self.toggle_email_alarm)
        self.emailConfigButton.clicked.connect(self.open_email_config_popup)

        # 🔹 로딩 스피너 추가
        self.spinner = QLabel(self.video_label)
        self.spinner.setFixedSize(480, 480)
        self.spinner.setAlignment(Qt.AlignCenter)
        self.spinner.setScaledContents(True)
        self.spinner.setStyleSheet("background-color: rgba(0, 0, 0, 80); border-radius: 10px;")

        spinner_path = os.path.join(os.path.dirname(__file__), "../resources/icons/spinner.gif")
        spinner_path = os.path.normpath(spinner_path)


        self.spinner_movie = QMovie(spinner_path)
        self.spinner.setMovie(self.spinner_movie)
        self.spinner_movie.start()
        # self.spinner.show()
        self.spinner.hide()

        self.update_button_states(False)

        init_roi_labels(self)

    def toggle_mediapipe_detection(self, checked):
        self.mediapipe_enabled = checked

        if self.mediapipe_enabled:
            # YOLO 강제 활성화
            if not self.yolo_enabled:
                self.yolo_enabled = True
                self.yolo_button.setChecked(True)
                if self.yolo_detector is None:
                    self.yolo_detector = YOLODetector()
                self.yolo_button.setText("YOLO ON")
                self.log("MediaPipe를 위해 YOLO 자동 활성화됨")

            # MediaPipe 활성화
            if self.pose_detector is None:
                self.pose_detector = MediaPipePoseDetector(main_window=self)
            self.mediaPipeButton.setText("MediaPipe ON")
            self.log("MediaPipe 포즈 인식 활성화됨")

        else:
            # MediaPipe 비활성화
            self.mediaPipeButton.setText("MediaPipe OFF")
            self.log("MediaPipe 포즈 인식 비활성화됨")

            # YOLO도 함께 끄기
            if self.yolo_enabled:
                self.yolo_enabled = False
                self.yolo_button.setChecked(False)
                self.yolo_button.setText("YOLO OFF")
                self.log("MediaPipe 해제로 인해 YOLO도 비활성화됨")



    def open_roi_popup(self):
        ip = self.ip_input.text().strip()
        user_id = self.id_input.text().strip()
        user_pw = self.pw_input.text().strip()

        if not ip or not user_id or not user_pw:
            QMessageBox.warning(self, "입력 오류", "IP, ID, PW를 모두 입력하세요.")
            return

        self.roi_popup = SetROIPopup(ip, user_id, user_pw, main_window=self, parent=self)

        self.roi_popup.show()

    def handle_nuc_once(self):
        pass # TODO: NUC 즉시 실행 기능 추후 구현

    def get_ip_auth(self):
        ip = self.ip_input.text().strip()
        user_id = self.id_input.text().strip()
        user_pw = self.pw_input.text().strip()
        if not ip or not user_id or not user_pw:
            QMessageBox.warning(self, "입력 오류", "IP, ID, PW를 모두 입력하세요.")
            return None
        return ip, user_id, user_pw

    def open_popup(self, popup_cls, attr_name):
        result = self.get_ip_auth()
        if not result:
            return
        ip, user_id, user_pw = result
        setattr(self, attr_name, popup_cls(ip, user_id, user_pw, self))
        getattr(self, attr_name).show()

    def open_image_control_popup(self):
        self.open_popup(ImageControlPopup, "image_popup")

    def open_display_control_popup(self):
        self.open_popup(DisplayControlPopup, "display_popup")

    def open_enhancement_control_popup(self):
        self.open_popup(EnhancementControlPopup, "enhancement_popup")

    def open_correction_control_popup(self):
        self.open_popup(CorrectionControlPopup, "correction_popup")

    def open_nuc_control_popup(self):
        self.open_popup(NUCControlPopup, "nuc_popup")

    def open_roi_popup(self):
        self.open_popup(SetROIPopup, "roi_popup")

    def toggle_popup_alarm(self, checked):
        self.alarm_settings["popup"] = checked
        self.log(f"팝업 알람 {'ON' if checked else 'OFF'}")

    def toggle_sound_alarm(self, checked):
        self.alarm_settings["sound"] = checked
        self.log(f"사운드 알람 {'ON' if checked else 'OFF'}")

    def toggle_email_alarm(self, checked):
        self.alarm_settings["email"] = checked
        self.log(f"이메일 알람 {'ON' if checked else 'OFF'}")

    def open_email_config_popup(self):
        self.email_popup = EmailConfigPopup(self)
        self.email_popup.exec_()
                    
    def check_alarm_trigger(self):
        """알람 조건 평가 및 알림 실행"""
        if not self.roi_alarm_config or not self.thermal_data:
            return

        # 3초 간격 제한
        now = time.time()
        if now - self.last_alarm_time < 3:
            return  # 최근 알람 후 3초 이내이면 무시

        triggered_rois = evaluate_alarms(self.roi_alarm_config, self.thermal_data)
        if not triggered_rois:
            return

        self.last_alarm_time = now  # 알람 발생 시각 갱신

        for roi in triggered_rois:
            roi_id = roi["roi_id"]
            temp = roi["temperature"]
            threshold = roi["threshold"]
            mode = roi["mode"]
            cond = roi["condition"]

            msg = f"[ROI {roi_id}] {mode} 온도 {temp:.1f}℃가 기준 {threshold:.1f}℃을 {'초과' if cond == 'above' else '미만'}했습니다."

            if self.alarm_settings.get("popup"):
                show_popup(msg, main_window=self)
            if self.alarm_settings.get("sound"):
                play_sound()
            if self.alarm_settings.get("email"):
                send_email("열화상 카메라 알람 발생", msg, main_window=self)

            self.log(f"🔔 알람 발생: {msg}")
    
    def update_button_states(self, connected):
        # 비연결 시 활성화할 위젯
        enable_when_disconnected = [
            self.start_button,
            self.search_button,
            self.ip_input,
            self.id_input,
            self.pw_input,
        ]
        
        # 연결 시 활성화할 위젯
        enable_when_connected = [
            self.stop_button,
            self.time_plot_button,
            # self.nuc_button,
            self.focusInButton,
            self.focusOutButton,
            self.yolo_button,
        ]

        for widget in enable_when_disconnected:
            widget.setEnabled(not connected)

        for widget in enable_when_connected:
            widget.setEnabled(connected)

    def open_ip_selector(self):
        popup = IPSelectorPopup(self)
        if popup.exec_() == popup.Accepted:
            selected_ip = popup.get_selected_ip()
            if selected_ip:
                self.ip_input.setText(selected_ip)

    def open_graph_viewer(self):
        ip = self.ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "IP 오류", "IP 주소를 먼저 입력해 주세요.")
            return
        self.graph_window = GraphWindow(ip)
        self.graph_window.show()

    def closeEvent(self, event):
        stop_stream(self)
        if self.graph_window is not None:
            self.graph_window.close()
        super().closeEvent(event)
 
    def toggle_yolo_detection(self, checked):
        self.yolo_enabled = checked
        if self.yolo_enabled:
            if self.yolo_detector is None:
                self.yolo_detector = YOLODetector()
            self.yolo_button.setText("YOLO ON")
            self.log("Yolo ON")
        else:
            self.yolo_button.setText("YOLO OFF")
            self.log("Yolo OFF")

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        if hasattr(self, "log_console") and self.log_console:
            self.log_console.appendPlainText(line)
            self.log_console.moveCursor(QTextCursor.End)
        else:
            print(line)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "spinner"):
            cx = self.video_label.width() // 2 - self.spinner.width() // 2
            cy = self.video_label.height() // 2 - self.spinner.height() // 2
            self.spinner.move(cx, cy)


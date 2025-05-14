from PyQt5.QtWidgets import (
    QMainWindow,QMessageBox
)
from PyQt5.QtCore import QTimer
import os
import sys
from PyQt5 import uic

from thermalcam.core.roi import fetch_all_rois
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
from thermalcam.core.frame_reader import FrameReader
from thermalcam.ui.roi_display_handler import init_roi_labels, process_roi_display
from thermalcam.ui.stream_handler import (
    start_stream, stop_stream, update_frame
)
from thermalcam.ui.roi_display_handler import refresh_rois

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
        with importlib.resources.path("thermalcam.resources.ui", "viewer.ui") as ui_file:
            uic.loadUi(str(ui_file), self)

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
        self.focusSpeedSlider.setMinimum(1)
        self.focusSpeedSlider.setMaximum(100)
        self.focusSpeedSlider.setValue(50)

        self.yolo_enabled = False
        self.yolo_detector = None
        self.actionYolo.setCheckable(True)
        self.actionYolo.triggered.connect(self.toggle_yolo_detection)

        self.start_button.clicked.connect(lambda: start_stream(self))
        self.stop_button.clicked.connect(lambda: stop_stream(self))
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

        init_roi_labels(self)


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
            self.nuc_button,
            self.focusInButton,
            self.focusOutButton,
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

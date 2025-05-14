# thermalcam/ui/stream_handler.py

import cv2
import time
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel, QMessageBox
from thermalcam.core.roi import fetch_all_rois
from thermalcam.core.alarm import fetch_alarm_conditions
from thermalcam.core.camera_client import ThermalReceiver
from thermalcam.core.frame_reader import FrameReader
from thermalcam.ui.roi_display_handler import process_roi_display
from thermalcam.ui.roi_display_handler import refresh_rois
from thermalcam.ui.yolo_handler import handle_yolo_detection


def prepare_stream_metadata(viewer):
    ip = viewer.ip_input.text().strip()
    viewer.user_id = viewer.id_input.text().strip()
    viewer.user_pw = viewer.pw_input.text().strip()

    viewer.rois = fetch_all_rois(ip, viewer.user_id, viewer.user_pw)
    viewer.roi_alarm_config = fetch_alarm_conditions(ip, viewer.user_id, viewer.user_pw)

    if viewer.rois is None:
        QMessageBox.warning(viewer, "로그인 실패", "ID 또는 비밀번호가 올바르지 않습니다.")
        return False
    return True

def connect_video_stream(viewer):
    ip = viewer.ip_input.text().strip()
    port = 554
    rtsp_url = f"rtsp://{viewer.user_id}:{viewer.user_pw}@{ip}:{port}/stream1"

    stop_stream(viewer)

    viewer.video_label.setText("연결중...")
    viewer.video_label.repaint()

    viewer.reader = FrameReader(rtsp_url, viewer.DELAY_SEC)
    viewer.reader.start()

    if viewer.timer is None:
        viewer.timer = QTimer()
        viewer.timer.timeout.connect(lambda: update_frame(viewer))

    viewer.timer.start(33)

    viewer.receiver = ThermalReceiver(
        ip, viewer.THERMAL_PORT, viewer.thermal_data,
        lambda: refresh_rois(viewer),  # ← 람다로 감싸서 함수 객체 전달
        viewer.roi_alarm_config
    )
    viewer.receiver.start()

    viewer.update_button_states(True)
    QTimer.singleShot(5000, lambda: check_stream_timeout(viewer))

def start_stream(viewer):
    if prepare_stream_metadata(viewer):
        connect_video_stream(viewer)

def stop_stream(viewer):
    if viewer.timer:
        viewer.timer.stop()
        viewer.timer = None

    if viewer.reader:
        viewer.reader.stop()
        viewer.reader.join()
        viewer.reader = None

    if viewer.receiver:
        viewer.receiver.stop()
        viewer.receiver = None

def check_stream_timeout(viewer):
    now = time.time()
    if viewer.stream_start_time is None:
        viewer.stream_start_time = now
    elif now - viewer.stream_start_time > 5:
        stop_stream(viewer)
        viewer.video_label.setText("영상 수신 실패")
        return True
    return False

def get_current_frame(viewer):
    if viewer.reader and viewer.reader.running:
        return viewer.reader.get_delayed()
    return None

def update_frame(viewer):
    frame = get_current_frame(viewer)
    if frame is not None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w

        scale_x = viewer.video_label.width() / rgb.shape[1]
        scale_y = viewer.video_label.height() / rgb.shape[0]
        process_roi_display(viewer, rgb, scale_x, scale_y)

        if viewer.yolo_enabled:
            from thermalcam.ui.yolo_handler import handle_yolo_detection
            rgb = handle_yolo_detection(viewer, rgb)

        image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        viewer.video_label.setPixmap(QPixmap.fromImage(image))
        viewer.stream_start_time = time.time()
    else:
        check_stream_timeout(viewer)
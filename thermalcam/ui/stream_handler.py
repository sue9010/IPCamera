# thermalcam/ui/stream_handler.py

import cv2
import time
from PyQt5.QtCore import QTimer, Qt
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

    viewer.spinner_movie.start()
    viewer.spinner.show()

    viewer.reader = FrameReader(rtsp_url, viewer.DELAY_SEC)
    viewer.reader.start()

    if viewer.timer is None:
        viewer.timer = QTimer()
        viewer.timer.timeout.connect(lambda: update_frame(viewer))

    viewer.timer.start(33)

    viewer.receiver = ThermalReceiver(
        ip, viewer.THERMAL_PORT, viewer.thermal_data,
        on_roi_refresh=None,
        roi_data=viewer.roi_alarm_config 
    )
    viewer.receiver.start() 

    viewer.update_button_states(True)
    QTimer.singleShot(5000, lambda: check_stream_timeout(viewer))

    viewer.should_draw_rois = True

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

    viewer.stream_start_time = None
    viewer.update_button_states(False)
    
    if hasattr(viewer, "spinner") and viewer.spinner:
        viewer.spinner.hide()
    if hasattr(viewer, "spinner_movie") and viewer.spinner_movie:
        viewer.spinner_movie.stop()

    viewer.should_draw_rois = False

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

        # ✅ 스피너 숨김 (최초 프레임 도착 시)
        if viewer.spinner.isVisible():
            viewer.spinner.hide()
            viewer.spinner_movie.stop()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w

        scale_x = viewer.video_label.width() / rgb.shape[1]
        scale_y = viewer.video_label.height() / rgb.shape[0]
        process_roi_display(viewer, rgb, scale_x, scale_y)

        person_present = False
        if viewer.yolo_enabled:
            from thermalcam.ui.yolo_handler import handle_yolo_detection
            # YOLO 감지 (coords, confs, class_ids 포함)
            boxes, scores, class_ids = viewer.yolo_detector.detect(rgb)
            if any(cls == 0 for cls in class_ids):  # class_id 0은 사람
                person_present = True
            rgb = viewer.yolo_detector.draw_detections(rgb, (boxes, scores, class_ids))

        # 사람 있을 때만 MediaPipe 실행
        if viewer.mediapipe_enabled and viewer.pose_detector and person_present:
            rgb = viewer.pose_detector.detect_and_draw(rgb)

        # ✅ QLabel 크기에 맞게 QPixmap 리사이즈 (비율 유지)
        image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        scaled_pixmap = pixmap.scaled(viewer.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        viewer.video_label.setPixmap(scaled_pixmap)

        viewer.stream_start_time = time.time()

        # ✅ 알람 조건 평가 및 트리거
        if hasattr(viewer, "check_alarm_trigger"):
            viewer.check_alarm_trigger()
    else:
        check_stream_timeout(viewer)
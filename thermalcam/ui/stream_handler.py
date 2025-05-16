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
    # viewer.receiver.start() 

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

        if viewer.yolo_enabled:
            from thermalcam.ui.yolo_handler import handle_yolo_detection
            rgb = handle_yolo_detection(viewer, rgb)

        # 아래 주석 처리된 코드는, 
        # 1. ROI 내부에서 사람이 인식 되었을 경우 log를 내보내며 , 
        # 2. 평균 온도가 37.5 도 이상 일 경우 log를 내보내는 샘플코드임.

        # if viewer.yolo_enabled:
        #     from thermalcam.ui.yolo_handler import handle_yolo_detection
        #     rgb = handle_yolo_detection(viewer, rgb)

        #     # ROI 매핑 및 온도 기반 경고 출력
        #     coords, confs = viewer.yolo_detector.detect(rgb)
        #     for (x1, y1, x2, y2), conf in zip(coords, confs):
        #         cx = int((x1 + x2) / 2)
        #         cy = int((y1 + y2) / 2)

        #         for idx, roi in enumerate(viewer.rois):
        #             if not roi["used"]:
        #                 continue
        #             sx, sy, ex, ey = roi["coords"]
        #             if sx <= cx <= ex and sy <= cy <= ey:
        #                 temp_data = viewer.thermal_data.get(idx)
        #                 if temp_data:
        #                     avg_temp = float(temp_data.get("avr", 0))
        #                     log_msg = f"[ROI {idx}] 사람 인식됨 → Max: {temp_data['max']} / Min: {temp_data['min']} / Avg: {avg_temp}"
        #                     viewer.log(log_msg)

        #                     if avg_temp >= 37.5:
        #                         viewer.log(f"[⚠️ 경고] ROI {idx} 평균 온도 {avg_temp:.1f}°C ≥ 37.5°C → 체온 이상 감지")
        #                 break  # 중복 방지

        image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        viewer.video_label.setPixmap(QPixmap.fromImage(image))
        viewer.stream_start_time = time.time()

        # ✅ 알람 조건 평가 및 트리거
        if hasattr(viewer, "check_alarm_trigger"):
            viewer.check_alarm_trigger()
    else:
        check_stream_timeout(viewer)
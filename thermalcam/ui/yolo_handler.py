# thermalcam/ui/yolo_handler.py

import datetime
import os
import cv2
import numpy as np

def handle_yolo_detection(viewer, rgb):
    if viewer.yolo_detector is None:
        from thermalcam.core.yolo import YOLODetector
        viewer.yolo_detector = YOLODetector()

    # detect 함수가 coords, scores, class_ids를 반환하도록 수정됨
    boxes, scores, class_ids = viewer.yolo_detector.detect(rgb)

    if boxes.size > 0:
        # draw_detections 함수도 class_ids까지 받도록 수정됨
        rgb = viewer.yolo_detector.draw_detections(rgb, (boxes, scores, class_ids))

        now = datetime.datetime.now()
        if not hasattr(viewer, "last_capture_time") or viewer.last_capture_time is None or \
           (now - viewer.last_capture_time).total_seconds() > 2:
            save_capture(rgb, now)
            viewer.last_capture_time = now

    return rgb

def save_capture(rgb, timestamp):
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    capture_dir = os.path.join(desktop_path, "capture")
    os.makedirs(capture_dir, exist_ok=True)
    filename = f"capture_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
    filepath = os.path.join(capture_dir, filename)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    cv2.putText(bgr, timestamp.strftime("%Y-%m-%d %H:%M:%S"), (10, bgr.shape[0]-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(filepath, bgr)
    print(f"[YOLO 캡처] 저장됨: {filepath}")

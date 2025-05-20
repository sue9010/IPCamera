import os
import sys
import cv2
import numpy as np
from ultralytics import YOLO

def resource_path(relative_path):
    try:
        # PyInstaller 실행 환경
        base_path = sys._MEIPASS
    except AttributeError:
        # 개발 중 실행 환경
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class YOLODetector:
    def __init__(self, model_path='thermalcam/resources/models/yolov8n.pt'):
        self.device = 'cpu'
        model_full_path = resource_path(model_path)
        self.model = YOLO(model_full_path).to(self.device)

        self.allowed_classes = {
            0,   # person
            15,  # cat
            16,  # dog
            17,  # horse
            18,  # sheep
            19,  # cow
            20,  # elephant
            21,  # bear
            22,  # zebra
            23,  # giraffe
        }

    def detect(self, frame):
        results = self.model.predict(source=frame, device=self.device, verbose=False)
        boxes = results[0].boxes
        coords = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        class_ids = boxes.cls.cpu().numpy().astype(int)

        filtered = [(c, conf, cls_id) for c, conf, cls_id in zip(coords, confs, class_ids)
                    if cls_id in self.allowed_classes and conf >= 0.5]

        if not filtered:
            return np.array([]), np.array([]), np.array([])

        coords, confs, class_ids = zip(*filtered)
        return np.array(coords), np.array(confs), np.array(class_ids)

    def draw_detections(self, frame, detections):
        coords, confs, class_ids = detections
        names = self.model.names

        for (x1, y1, x2, y2), conf, cls_id in zip(coords, confs, class_ids):
            label = f"{names[cls_id]} {conf:.2f}"
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(frame, label, (int(x1), int(y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return frame

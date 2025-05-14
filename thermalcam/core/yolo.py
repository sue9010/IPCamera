# yolo_detector.py
from ultralytics import YOLO
import cv2

class YOLODetector:
    def __init__(self, model_path='yolov8n.pt'):
        self.device = 'cpu'  # 강제로 CPU 사용
        self.model = YOLO(model_path).to(self.device)

    def detect(self, frame):
        results = self.model.predict(source=frame, device=self.device, verbose=False)
        boxes = results[0].boxes
        return boxes.xyxy.cpu().numpy(), boxes.conf.cpu().numpy()

    def draw_detections(self, frame, detections):
        coords, confs = detections
        for (x1, y1, x2, y2), conf in zip(coords, confs):
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(frame, f"Person {conf:.2f}", (int(x1), int(y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return frame

from ultralytics import YOLO
import cv2
import numpy as np

class YOLODetector:
    def __init__(self, model_path='yolov8n.pt'):
        self.device = 'cpu'
        self.model = YOLO(model_path).to(self.device)
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

        # 사람과 주요 동물 클래스만 필터링
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

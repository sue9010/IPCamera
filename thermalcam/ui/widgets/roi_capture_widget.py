# ROI/roi_capture_widget.py
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPainter, QPen

class ROICaptureLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dragging = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.on_roi_drawn = None  # 외부 콜백 (SetROIPopup에서 연결)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.dragging = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            self.end_point = event.pos()
            self.update()

            if self.on_roi_drawn:
                # 좌표 정규화 후 전달
                x1, y1 = self.start_point.x(), self.start_point.y()
                x2, y2 = self.end_point.x(), self.end_point.y()
                self.on_roi_drawn(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.dragging:
            painter = QPainter(self)
            pen = QPen(Qt.green, 1, Qt.SolidLine)
            painter.setPen(pen)
            rect = QRect(self.start_point, self.end_point)
            painter.drawRect(rect.normalized())

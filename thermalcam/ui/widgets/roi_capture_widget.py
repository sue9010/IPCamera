from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPainter, QPen
 
class ROICaptureLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dragging = False
        self.dragging_roi = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.drag_start_pos = QPoint()

        self.selected_row = None
        self.roi_rects = []  # (row, QRect) 리스트 - 드로어가 설정

        self.on_roi_drawn = None         # ROI 새로 그릴 때
        self.on_roi_selected = None      # ROI 클릭해서 선택했을 때
        self.on_roi_moved = None         # ROI 클릭 후 드래그로 이동했을 때

        self.move_dx = 0
        self.move_dy = 0

        self.image_width = 640    # 기본값, 외부에서 설정 필요
        self.image_height = 480   # 기본값, 외부에서 설정 필요

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # ✅ ROI 클릭 감지 → 이동 준비
            for row, rect in self.roi_rects:
                if rect.contains(event.pos()):
                    self.selected_row = row
                    self.dragging_roi = True
                    self.drag_start_pos = event.pos()

                    if self.on_roi_selected:
                        self.on_roi_selected(row)
                    return

            # ❌ ROI 클릭 아님 → 새 ROI 드래그
            self.selected_row = None
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.dragging = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.end_point = event.pos()
            self.update()
        elif self.dragging_roi:
            dx = event.pos().x() - self.drag_start_pos.x()
            dy = event.pos().y() - self.drag_start_pos.y()

            # ROI 이동 제한
            for row, rect in self.roi_rects:
                if row == self.selected_row:
                    if rect.left() + dx < 0:
                        dx = -rect.left()
                    if rect.top() + dy < 0:
                        dy = -rect.top()
                    if rect.right() + dx > self.image_width:
                        dx = self.image_width - rect.right()
                    if rect.bottom() + dy > self.image_height:
                        dy = self.image_height - rect.bottom()
                    break

            self.move_dx = dx
            self.move_dy = dy
            self.update()

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            self.end_point = event.pos()
            self.update()

            if self.on_roi_drawn:
                x1, y1 = self.start_point.x(), self.start_point.y()
                x2, y2 = self.end_point.x(), self.end_point.y()
                self.on_roi_drawn(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

        elif self.dragging_roi:
            self.dragging_roi = False
            end_pos = event.pos()
            dx = end_pos.x() - self.drag_start_pos.x()
            dy = end_pos.y() - self.drag_start_pos.y()

            # ✅ 다시 한 번 제한 적용
            for row, rect in self.roi_rects:
                if row == self.selected_row:
                    if rect.left() + dx < 0:
                        dx = -rect.left()
                    if rect.top() + dy < 0:
                        dy = -rect.top()
                    if rect.right() + dx > self.image_width:
                        dx = self.image_width - rect.right()
                    if rect.bottom() + dy > self.image_height:
                        dy = self.image_height - rect.bottom()
                    break


            if abs(dx) > 1 or abs(dy) > 1:
                if self.on_roi_moved and self.selected_row is not None:
                    self.on_roi_moved(self.selected_row, dx, dy)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)

        if self.dragging:
            pen = QPen(Qt.green, 1, Qt.SolidLine)
            painter.setPen(pen)
            rect = QRect(self.start_point, self.end_point)
            painter.drawRect(rect.normalized())

        elif self.dragging_roi and self.selected_row is not None:
            # 선택된 ROI rect를 찾아서 이동된 위치에 그림
            for row, rect in self.roi_rects:
                if row == self.selected_row:
                    moved_rect = rect.translated(self.move_dx, self.move_dy)
                    pen = QPen(Qt.red, 1, Qt.DashLine)
                    painter.setPen(pen)
                    painter.drawRect(moved_rect.normalized())
                    break

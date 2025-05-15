import cv2
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtWidgets import QCheckBox
 
class ROIDrawer:
    def __init__(self, roi_table, capture_label):
        """
        roi_table: QTableWidget containing ROI data
        capture_label: QLabel (또는 ROICaptureLabel), 결과 이미지를 표시할 위젯
        """
        self.roi_table = roi_table
        self.capture_label = capture_label
        self.frame_original = None  # 외부에서 set_frame()으로 설정 필요

    def set_frame(self, frame):
        self.frame_original = frame.copy()

    def draw_rois_on_image(self):
        if self.frame_original is None:
            return

        frame = self.frame_original.copy()
        for row in range(10):
            try:
                chk_widget = self.roi_table.cellWidget(row, 0)
                chk = chk_widget.findChild(QCheckBox) if chk_widget else None
                if not chk or not chk.isChecked():
                    continue

                startx = int(self.roi_table.item(row, 1).text())
                starty = int(self.roi_table.item(row, 2).text())
                endx = int(self.roi_table.item(row, 3).text())
                endy = int(self.roi_table.item(row, 4).text())

                cv2.rectangle(frame, (startx, starty), (endx, endy), (0, 255, 0), 1)

                # ROI 번호 텍스트
                cx = (startx + endx) // 2
                cy = (starty + endy) // 2
                cv2.putText(frame, f"{row}", (cx - 10, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)

            except Exception as e:
                print(f"[ROI {row}] 그리기 실패:", e)

        self.update_capture_display(frame)

        self.capture_label.roi_rects = []  # ✅ ROI 사각형 초기화

        for row in range(10):
            try:
                chk_widget = self.roi_table.cellWidget(row, 0)
                chk = chk_widget.findChild(QCheckBox) if chk_widget else None
                if not chk or not chk.isChecked():
                    continue

                startx = int(self.roi_table.item(row, 1).text())
                starty = int(self.roi_table.item(row, 2).text())
                endx = int(self.roi_table.item(row, 3).text())
                endy = int(self.roi_table.item(row, 4).text())

                # ✅ ROI 사각형 저장
                rect = QRect(startx, starty, endx - startx, endy - starty).normalized()
                self.capture_label.roi_rects.append((row, rect))

                # 그리기 (기존 코드 유지)
                cv2.rectangle(frame, (startx, starty), (endx, endy), (0, 255, 0), 1)
                cx = (startx + endx) // 2
                cy = (starty + endy) // 2
                cv2.putText(frame, f"{row}", (cx - 10, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)

            except Exception as e:
                print(f"[ROI {row}] 그리기 실패:", e)


    def update_capture_display(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.capture_label.setPixmap(QPixmap.fromImage(qimg).scaled(
            self.capture_label.width(), self.capture_label.height(), Qt.KeepAspectRatio
        ))

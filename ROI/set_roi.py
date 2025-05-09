from PyQt5.QtWidgets import (
    QDialog, QCheckBox, QRadioButton, QWidget, QHBoxLayout,
    QTableWidgetItem, QMessageBox, QButtonGroup, QLabel, QPushButton, QTableWidget
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5 import uic
from PyQt5.QtCore import Qt
import os
import cv2
import requests
from ROI.roi_capture_widget import ROICaptureLabel

class SetROIPopup(QDialog):
    def __init__(self, ip, user_id, user_pw, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.user_id = user_id
        self.user_pw = user_pw

        uic.loadUi(os.path.join(os.path.dirname(__file__), "roi.ui"), self)
        self.setWindowTitle("ROI 설정")

        # Promoted QLabel → ROICaptureLabel 이기 때문에 그대로 받아오면 됨
        self.capture_image = self.findChild(ROICaptureLabel, "capture_image")
        self.capture_image.on_roi_drawn = self.handle_roi_drawn

        self.roi_table = self.findChild(QTableWidget, "roi_table")
        self.save_button = self.findChild(QPushButton, "btn_save")
        if self.save_button:
            self.save_button.clicked.connect(self.save_all_rois)
        
        self.frame_original = None
        self.load_rtsp_frame()
        self.load_roi_data()



    def load_rtsp_frame(self):
        try:
            rtsp_url = f"rtsp://{self.ip}:554/stream1"
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            ret, frame = cap.read()
            cap.release()
            if not ret:
                raise RuntimeError("RTSP 프레임 캡처 실패")

            self.frame_original = frame.copy()
            self.resolution = (frame.shape[1], frame.shape[0])  # ← 여기 추가!
            self.update_capture_display(frame)

        except Exception as e:
            QMessageBox.critical(self, "RTSP 오류", f"프레임 캡처 실패:\n{str(e)}")


    def update_capture_display(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.capture_image.setPixmap(QPixmap.fromImage(qimg).scaled(
            self.capture_image.width(), self.capture_image.height(), Qt.KeepAspectRatio
        ))

    def load_roi_data(self):
        self.roi_table.setRowCount(11)  # Entire + ROI 0~9
        self.roi_table.setColumnCount(6)
        self.roi_table.setHorizontalHeaderLabels([
            "is_used", "Start X", "Start Y", "End X", "End Y", "selected"
        ])

        self.radio_group = QButtonGroup(self)
        self.radio_group.setExclusive(True)

        # ▶ Entire ROI (row 0)
        entire_chk_widget = QWidget()
        layout = QHBoxLayout(entire_chk_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(QCheckBox())  # 비어있는 체크박스
        self.roi_table.setCellWidget(0, 0, entire_chk_widget)

        self.roi_table.setItem(0, 1, QTableWidgetItem("0"))
        self.roi_table.setItem(0, 2, QTableWidgetItem("0"))

        width, height = self.resolution if hasattr(self, "resolution") else (640, 480)
        self.roi_table.setItem(0, 3, QTableWidgetItem(str(width)))
        self.roi_table.setItem(0, 4, QTableWidgetItem(str(height)))

        radio_widget = QWidget()
        rlayout = QHBoxLayout(radio_widget)
        rlayout.setContentsMargins(0, 0, 0, 0)
        rlayout.setAlignment(Qt.AlignCenter)
        rlayout.addWidget(QRadioButton())
        self.roi_table.setCellWidget(0, 5, radio_widget)

        # ▶ ROI 0~9 (row 1~10)
        for roi_id in range(10):
            row = roi_id + 1
            url = f"http://{self.ip}/cgi-bin/control/camthermalroi.cgi"
            params = {
                "id": self.user_id,
                "passwd": self.user_pw,
                "action": f"getthermalroi{roi_id}"
            }
            try:
                resp = requests.get(url, params=params, timeout=2)
                if resp.status_code != 200 or "Error" in resp.text:
                    continue

                data = dict(line.split("=", 1) for line in resp.text.strip().splitlines() if "=" in line)

                # is_used
                chk = QCheckBox()
                chk.setChecked(data.get("roi_use", "off") == "on")
                chk.stateChanged.connect(self.draw_rois_on_image)
                chk_widget = QWidget()
                layout = QHBoxLayout(chk_widget)
                layout.addWidget(chk)
                layout.setAlignment(Qt.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)
                self.roi_table.setCellWidget(row, 0, chk_widget)

                coords = ["startx", "starty", "endx", "endy"]
                for i, key in enumerate(coords, start=1):
                    item = QTableWidgetItem(data.get(key, "0"))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.roi_table.setItem(row, i, item)

                radio = QRadioButton()
                radio_widget = QWidget()
                rlayout = QHBoxLayout(radio_widget)
                rlayout.addWidget(radio)
                rlayout.setAlignment(Qt.AlignCenter)
                rlayout.setContentsMargins(0, 0, 0, 0)
                self.radio_group.addButton(radio)
                self.roi_table.setCellWidget(row, 5, radio_widget)

            except Exception as e:
                print(f"[ROI {roi_id}] 로딩 실패:", e)

        self.draw_rois_on_image()


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

                # 가운데에 ROI 번호 출력
                cx = (startx + endx) // 2
                cy = (starty + endy) // 2
                cv2.putText(frame, f"{row}", (cx - 10, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
                
            except Exception as e:
                print(f"[ROI {row}] 그리기 실패:", e)

        self.update_capture_display(frame)

    def handle_roi_drawn(self, x1, y1, x2, y2):
        # 선택된 ROI 찾아서 테이블 갱신
        for row in range(10):
            radio_widget = self.roi_table.cellWidget(row, 5)
            if not radio_widget:
                continue
            radio = radio_widget.findChild(QRadioButton)
            if radio and radio.isChecked():
                self.roi_table.item(row, 1).setText(str(x1))
                self.roi_table.item(row, 2).setText(str(y1))
                self.roi_table.item(row, 3).setText(str(x2))
                self.roi_table.item(row, 4).setText(str(y2))
                break
        self.draw_rois_on_image()


    def save_all_rois(self):
        for row in range(10):
            try:
                chk_widget = self.roi_table.cellWidget(row, 0)
                chk = chk_widget.findChild(QCheckBox) if chk_widget else None
                roi_use = "on" if chk and chk.isChecked() else "off"

                startx = int(self.roi_table.item(row, 1).text())
                starty = int(self.roi_table.item(row, 2).text())
                endx = int(self.roi_table.item(row, 3).text())
                endy = int(self.roi_table.item(row, 4).text())

                url = f"http://{self.ip}/cgi-bin/control/camthermalroi.cgi"
                params = {
                    "id": self.user_id,
                    "passwd": self.user_pw,
                    "action": f"setthermalroi{row}",
                    "roi_use": roi_use,
                    "startx": startx,
                    "starty": starty,
                    "endx": endx,
                    "endy": endy
                }

                resp = requests.get(url, params=params, timeout=2)
                if resp.status_code != 200 or "Error" in resp.text:
                    print(f"[ROI {row}] 설정 실패: {resp.text}")
            except Exception as e:
                print(f"[ROI {row}] 저장 중 예외 발생:", e)

        QMessageBox.information(self, "저장 완료", "모든 ROI 설정이 저장되었습니다.")

from PyQt5.QtWidgets import (
    QDialog, QCheckBox, QRadioButton, QWidget, QHBoxLayout,
    QTableWidgetItem, QMessageBox, QButtonGroup, QPushButton, QTableWidget,QComboBox
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5 import uic
from PyQt5.QtCore import Qt
import os
import cv2
import requests
from ROI.roi_capture_widget import ROICaptureLabel
from roi_utils import fetch_all_rois 
from ROI.alarm_roi import fetch_alarm_conditions 

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
            self.save_button.clicked.connect(self.save_alarm_data)
        
        self.frame_original = None
        self.load_rtsp_frame()
        self.load_roi_data()
        self.load_alarm_data()



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
        self.roi_table.setRowCount(10)
        self.roi_table.setColumnCount(6)
        self.roi_table.setHorizontalHeaderLabels([
            "is_used", "Start X", "Start Y", "End X", "End Y", "selected"
        ])

        self.radio_group = QButtonGroup(self)
        self.radio_group.setExclusive(True)

        roi_list = fetch_all_rois(self.ip, self.user_id, self.user_pw)
        if roi_list is None or len(roi_list) < 10:
            roi_list = [{} for _ in range(10)]

        for row in range(10):
            roi = roi_list[row] if row < len(roi_list) else {}

            # ✅ 사용 여부와 좌표 가져오기
            roi_use = roi.get("used", False)
            coords = roi.get("coords", (0, 0, 0, 0))
            sx, sy, ex, ey = coords if len(coords) == 4 else (0, 0, 0, 0)

            # ▷ 체크박스 (roi_use)
            chk = QCheckBox()
            chk.setChecked(roi_use)  # ✅ 사용 여부 반영
            chk.stateChanged.connect(self.draw_rois_on_image)
            chk_widget = QWidget()
            layout = QHBoxLayout(chk_widget)
            layout.addWidget(chk)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            self.roi_table.setCellWidget(row, 0, chk_widget)

            # ▷ 좌표 셀
            for col, val in zip(range(1, 5), [sx, sy, ex, ey]):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.roi_table.setItem(row, col, item)

            # ▷ 라디오 버튼
            radio = QRadioButton()
            radio.setChecked(False)
            radio_widget = QWidget()
            rlayout = QHBoxLayout(radio_widget)
            rlayout.addWidget(radio)
            rlayout.setAlignment(Qt.AlignCenter)
            rlayout.setContentsMargins(0, 0, 0, 0)
            self.radio_group.addButton(radio)
            self.roi_table.setCellWidget(row, 5, radio_widget)

        # ✅ draw는 체크된 ROI만 처리 (이미 함수 내부에서 필터됨)
        self.draw_rois_on_image()

    def load_alarm_data(self):
        if not self.alarm_table:
            print("[SetROIPopup] alarm_table 연결 안됨")
            return

        self.alarm_table.setRowCount(10)
        self.alarm_table.setColumnCount(7)
        self.alarm_table.setHorizontalHeaderLabels([
            "is_used", "Mode", "Condition", "Temperature", "Start Delay", "Stop Delay", "Alarm Out"
        ])
        self.alarm_table.setVerticalHeaderLabels([str(i) for i in range(10)])

        roi_list = fetch_all_rois(self.ip, self.user_id, self.user_pw)
        alarm_list = fetch_alarm_conditions(self.ip, self.user_id, self.user_pw)

        if roi_list is None or len(roi_list) < 10:
            roi_list = [{} for _ in range(10)]
        if not alarm_list or len(alarm_list) < 10:
            alarm_list = [{} for _ in range(10)]

        for i in range(10):
            roi = roi_list[i]
            alarm = alarm_list[i]

            # ✅ ROI 사용 여부 체크박스 (is_used)
            chk = QCheckBox()
            chk.setChecked(roi.get("used", False))
            chk_widget = QWidget()
            layout = QHBoxLayout(chk_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setAlignment(Qt.AlignCenter)
            layout.addWidget(chk)
            self.alarm_table.setCellWidget(i, 0, chk_widget)

            # 🔽 Mode 드롭다운
            mode_box = QComboBox()
            mode_box.addItems(["maximum", "minimum", "average"])
            mode_box.setCurrentText(alarm.get("mode", "maximum"))
            self.alarm_table.setCellWidget(i, 1, mode_box)

            # 🔽 Condition 드롭다운
            cond_box = QComboBox()
            cond_box.addItems(["above", "below"])
            cond_box.setCurrentText(alarm.get("condition", "above"))
            self.alarm_table.setCellWidget(i, 2, cond_box)

            # 🌡 온도 및 딜레이 (일반 셀)
            for col, key in zip(range(3, 6), ["temperature", "start_delay", "stop_delay"]):
                val = alarm.get(key, "")
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.alarm_table.setItem(i, col, item)

            # 🔽 Alarm Out 드롭다운
            out_box = QComboBox()
            out_box.addItems(["none", "1", "2"])
            out_box.setCurrentText(alarm.get("alarm_out", "none"))
            self.alarm_table.setCellWidget(i, 6, out_box)

        # ✅ 열 너비를 자동으로 조절
        self.alarm_table.resizeColumnsToContents()


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

    def save_alarm_data(self):
        success = True
        for row in range(10):
            try:
                mode_box = self.alarm_table.cellWidget(row, 0)
                cond_box = self.alarm_table.cellWidget(row, 1)
                alarm_out_box = self.alarm_table.cellWidget(row, 5)

                mode = mode_box.currentText() if mode_box else "maximum"
                condition = cond_box.currentText() if cond_box else "above"
                alarm_out = alarm_out_box.currentText() if alarm_out_box else "none"

                temp_item = self.alarm_table.item(row, 2)
                start_item = self.alarm_table.item(row, 3)
                stop_item = self.alarm_table.item(row, 4)

                temperature = temp_item.text() if temp_item else ""
                start_delay = start_item.text() if start_item else ""
                stop_delay = stop_item.text() if stop_item else ""

                url = f"http://{self.ip}/cgi-bin/control/camthermalroi.cgi"
                params = {
                    "id": self.user_id,
                    "passwd": self.user_pw,
                    "action": f"setthermalroi{row}",
                    "mode": mode,
                    "condition": condition,
                    "temperature": temperature,
                    "start_delay": start_delay,
                    "stop_delay": stop_delay,
                    "alarm_out": alarm_out,
                    "alarm_use": "on"
                }

                resp = requests.get(url, params=params, timeout=2)
                if resp.status_code != 200 or "Error" in resp.text:
                    print(f"[Alarm ROI {row}] 저장 실패: {resp.text}")
                    success = False
            except Exception as e:
                print(f"[Alarm ROI {row}] 예외 발생:", e)
                success = False

        if success:
            QMessageBox.information(self, "저장 완료", "모든 알람 조건이 저장되었습니다.")
        else:
            QMessageBox.warning(self, "저장 실패", "일부 ROI 알람 조건 저장에 실패했습니다.")


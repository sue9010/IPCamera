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
            self.save_button.clicked.connect(self.save_all_roi_settings)

        
        self.frame_original = None
        self.load_rtsp_frame()
        self.load_roi_data()
        self.load_alarm_data()
        self.load_iso_data()

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

            roi_use = roi.get("used", False)
            coords = roi.get("coords", (0, 0, 0, 0))
            sx, sy, ex, ey = coords if len(coords) == 4 else (0, 0, 0, 0)

            # ✅ ROI 테이블 is_used 체크박스 + 동기화 연결
            chk = QCheckBox()
            chk.setChecked(roi_use)

            chk.stateChanged.connect(lambda state, r=row: self.on_is_used_changed(r, state))

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
        if not roi_list or len(roi_list) < 10:
            roi_list = [{} for _ in range(10)]

        for i in range(10):
            roi = roi_list[i]
            alarm = roi.get("alarm", {})

            # ✅ is_used 체크박스 생성 + ROI/ISO와 동기화
            chk = QCheckBox()
            chk.setChecked(roi.get("used", False))

            chk.stateChanged.connect(lambda state, r=i: self.on_is_used_changed(r, state))

            chk_widget = QWidget()
            layout = QHBoxLayout(chk_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setAlignment(Qt.AlignCenter)
            layout.addWidget(chk)
            self.alarm_table.setCellWidget(i, 0, chk_widget)

            # Mode
            mode_box = QComboBox()
            mode_box.addItems(["maximum", "minimum", "average"])
            mode_box.setCurrentText(alarm.get("mode", "maximum"))
            self.alarm_table.setCellWidget(i, 1, mode_box)

            # Condition
            cond_box = QComboBox()
            cond_box.addItems(["above", "below"])
            cond_box.setCurrentText(alarm.get("condition", "above"))
            self.alarm_table.setCellWidget(i, 2, cond_box)

            # Temp, Delays
            for col, key in zip(range(3, 6), ["temperature", "start_delay", "stop_delay"]):
                val = alarm.get(key, "")
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.alarm_table.setItem(i, col, item)

            # Alarm Out
            out_box = QComboBox()
            out_box.addItems(["none", "1", "2"])
            out_box.setCurrentText(alarm.get("alarm_out", "none"))
            self.alarm_table.setCellWidget(i, 6, out_box)

        self.alarm_table.resizeColumnsToContents()

    def load_iso_data(self):
        self.iso_table = self.findChild(QTableWidget, "iso_table")
        if not self.iso_table:
            print("[SetROIPopup] iso_table 연결 안됨")
            return

        self.iso_table.setRowCount(10)
        self.iso_table.setColumnCount(4)
        self.iso_table.setHorizontalHeaderLabels([
            "is_used", "Condition", "Temperature", "Color"
        ])
        self.iso_table.setVerticalHeaderLabels([str(i) for i in range(10)])

        roi_list = fetch_all_rois(self.ip, self.user_id, self.user_pw)
        if not roi_list or len(roi_list) < 10:
            roi_list = [{} for _ in range(10)]

        for i in range(10):
            roi = roi_list[i]
            iso = roi.get("iso", {})

            # ✅ is_used 체크박스 생성 + ROI/Alarm 동기화
            chk = QCheckBox()
            chk.setChecked(roi.get("used", False))

            chk.stateChanged.connect(lambda state, r=i: self.on_is_used_changed(r, state))

            chk_widget = QWidget()
            layout = QHBoxLayout(chk_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setAlignment(Qt.AlignCenter)
            layout.addWidget(chk)
            self.iso_table.setCellWidget(i, 0, chk_widget)

            # 🔽 Condition
            cond_box = QComboBox()
            cond_box.addItems(["above", "below"])
            cond_box.setCurrentText(iso.get("condition", "above"))
            self.iso_table.setCellWidget(i, 1, cond_box)

            # 🌡 Temperature
            temp = QTableWidgetItem(str(iso.get("temperature", "")))
            temp.setTextAlignment(Qt.AlignCenter)
            self.iso_table.setItem(i, 2, temp)

            # 🎨 Color
            color_box = QComboBox()
            color_box.addItems(["red", "green", "blue", "grey"])
            color_box.setCurrentText(iso.get("color", "red"))
            self.iso_table.setCellWidget(i, 3, color_box)

        self.iso_table.resizeColumnsToContents()


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

    def save_all_roi_settings(self):
        success = True

        for row in range(10):
            try:
                # ROI 탭에서 가져오기
                roi_chk = self.roi_table.cellWidget(row, 0)
                roi_checked = roi_chk.findChild(QCheckBox).isChecked() if roi_chk else False

                startx = int(self.roi_table.item(row, 1).text())
                starty = int(self.roi_table.item(row, 2).text())
                endx = int(self.roi_table.item(row, 3).text())
                endy = int(self.roi_table.item(row, 4).text())

                roi_use = "on" if roi_checked else "off"

                # 알람 탭에서 가져오기
                mode_box = self.alarm_table.cellWidget(row, 1)
                cond_box = self.alarm_table.cellWidget(row, 2)
                alarm_out_box = self.alarm_table.cellWidget(row, 6)

                mode = mode_box.currentText() if mode_box else "maximum"
                condition = cond_box.currentText() if cond_box else "above"
                alarm_out = alarm_out_box.currentText() if alarm_out_box else "none"

                temp_item = self.alarm_table.item(row, 3)
                start_item = self.alarm_table.item(row, 4)
                stop_item = self.alarm_table.item(row, 5)

                temperature = temp_item.text() if temp_item else ""
                start_delay = start_item.text() if start_item else ""
                stop_delay = stop_item.text() if stop_item else ""

                alarm_use = "on" if roi_checked else "off"

                # ISO 탭에서 가져오기
                iso_chk = self.iso_table.cellWidget(row, 0)
                iso_checked = iso_chk.findChild(QCheckBox).isChecked() if iso_chk else False

                iso_cond_box = self.iso_table.cellWidget(row, 1)
                iso_temp_item = self.iso_table.item(row, 2)
                iso_color_box = self.iso_table.cellWidget(row, 3)

                iso_condition = iso_cond_box.currentText() if iso_cond_box else "above"
                iso_temperature = iso_temp_item.text() if iso_temp_item else ""
                iso_color = iso_color_box.currentText() if iso_color_box else "red"
                iso_use = "on" if iso_checked else "off"

                # 요청 전송
                url = f"http://{self.ip}/cgi-bin/control/camthermalroi.cgi"
                params = {
                    "id": self.user_id,
                    "passwd": self.user_pw,
                    "action": f"setthermalroi{row}",
                    "roi_use": roi_use,
                    "startx": startx,
                    "starty": starty,
                    "endx": endx,
                    "endy": endy,
                    "alarm_use": alarm_use,
                    "mode": mode,
                    "condition": condition,
                    "temperature": temperature,
                    "start_delay": start_delay,
                    "stop_delay": stop_delay,
                    "alarm_out": alarm_out,
                    "iso_use": iso_use,
                    "iso_color": iso_color
                }

                # ISO 관련 조건/온도는 기존 alarm 조건과 겹치므로 재활용
                if iso_use == "on":
                    params["condition"] = iso_condition
                    params["temperature"] = iso_temperature

                resp = requests.get(url, params=params, timeout=2)
                if resp.status_code != 200 or "Error" in resp.text:
                    print(f"[ROI {row}] 저장 실패: {resp.text}")
                    success = False

            except Exception as e:
                print(f"[ROI {row}] 저장 중 예외 발생:", e)
                success = False

        if success:
            QMessageBox.information(self, "저장 완료", "모든 ROI/알람/ISO 설정이 저장되었습니다.")
        else:
            QMessageBox.warning(self, "저장 실패", "일부 ROI 설정 저장에 실패했습니다.")

    def on_is_used_changed(self, row, state):
        """특정 row의 is_used 체크 상태가 바뀌면 모든 테이블에 동기화"""
        tables = [self.roi_table, self.alarm_table, self.iso_table]

        for table in tables:
            try:
                if not table:
                    continue
                widget = table.cellWidget(row, 0)
                if not widget:
                    continue
                chk = widget.findChild(QCheckBox)
                # 상태가 다르면만 갱신 (루프 방지)
                if chk and chk.isChecked() != (state == Qt.Checked):
                    chk.blockSignals(True)
                    chk.setChecked(state == Qt.Checked)
                    chk.blockSignals(False)
            except Exception as e:
                print(f"[is_used 동기화 오류] {table.objectName()} row {row}: {e}")
        
        self.draw_rois_on_image()

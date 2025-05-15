from PyQt5.QtWidgets import QCheckBox, QComboBox, QTableWidgetItem, QWidget, QHBoxLayout, QRadioButton, QButtonGroup
from PyQt5.QtCore import Qt
from thermalcam.core.roi import fetch_all_rois

class ROILoader:
    def __init__(self, ip, user_id, user_pw, roi_table, alarm_table, iso_table):
        self.ip = ip
        self.user_id = user_id
        self.user_pw = user_pw
        self.roi_table = roi_table
        self.alarm_table = alarm_table
        self.iso_table = iso_table

    def load_all(self):
        self.load_roi_data()
        self.load_alarm_data()
        self.load_iso_data()

    def load_roi_data(self):
        self.roi_table.setRowCount(10)
        self.roi_table.setColumnCount(6)
        self.roi_table.setHorizontalHeaderLabels(["is_used", "Start X", "Start Y", "End X", "End Y", "selected"])

        # 🔥 radio 그룹 설정 (단일 선택 전용)
        self.radio_group = QButtonGroup()
        self.radio_group.setExclusive(True)

        roi_list = fetch_all_rois(self.ip, self.user_id, self.user_pw) or [{} for _ in range(10)]

        for row in range(10):
            roi = roi_list[row] if row < len(roi_list) else {}
            roi_use = roi.get("used", False)
            coords = roi.get("coords", (0, 0, 0, 0))
            sx, sy, ex, ey = coords if len(coords) == 4 else (0, 0, 0, 0)

            # ✅ is_used 체크박스
            chk = QCheckBox()
            chk.setChecked(roi_use)
            chk_widget = QWidget()
            layout = QHBoxLayout(chk_widget)
            layout.addWidget(chk)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            self.roi_table.setCellWidget(row, 0, chk_widget)

            # ✅ 좌표 아이템
            for col, val in zip(range(1, 5), [sx, sy, ex, ey]):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.roi_table.setItem(row, col, item)

            # ✅ selected: 라디오 버튼 (단일 선택)
            radio = QRadioButton()
            radio_widget = QWidget()
            rlayout = QHBoxLayout(radio_widget)
            rlayout.addWidget(radio)
            rlayout.setAlignment(Qt.AlignCenter)
            rlayout.setContentsMargins(0, 0, 0, 0)
            self.roi_table.setCellWidget(row, 5, radio_widget)
            self.radio_group.addButton(radio, row)

    def load_alarm_data(self):
        if not self.alarm_table:
            return
        self.alarm_table.setRowCount(10)
        self.alarm_table.setColumnCount(7)
        self.alarm_table.setHorizontalHeaderLabels(["is_used", "Mode", "Condition", "Temperature", "Start Delay", "Stop Delay", "Alarm Out"])
        self.alarm_table.setVerticalHeaderLabels([str(i) for i in range(10)])
        roi_list = fetch_all_rois(self.ip, self.user_id, self.user_pw) or [{} for _ in range(10)]

        for i in range(10):
            roi = roi_list[i]
            alarm = roi.get("alarm", {})
            chk = QCheckBox()
            chk.setChecked(roi.get("used", False))
            chk_widget = QWidget()
            layout = QHBoxLayout(chk_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setAlignment(Qt.AlignCenter)
            layout.addWidget(chk)
            self.alarm_table.setCellWidget(i, 0, chk_widget)

            mode_box = QComboBox()
            mode_box.addItems(["maximum", "minimum", "average"])
            mode_box.setCurrentText(alarm.get("mode", "maximum"))
            self.alarm_table.setCellWidget(i, 1, mode_box)

            cond_box = QComboBox()
            cond_box.addItems(["above", "below"])
            cond_box.setCurrentText(alarm.get("condition", "above"))
            self.alarm_table.setCellWidget(i, 2, cond_box)

            for col, key in zip(range(3, 6), ["temperature", "start_delay", "stop_delay"]):
                val = alarm.get(key, "")
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.alarm_table.setItem(i, col, item)

            out_box = QComboBox()
            out_box.addItems(["none", "1", "2"])
            out_box.setCurrentText(alarm.get("alarm_out", "none"))
            self.alarm_table.setCellWidget(i, 6, out_box)

        self.alarm_table.resizeColumnsToContents()

    def load_iso_data(self):
        if not self.iso_table:
            return
        self.iso_table.setRowCount(10)
        self.iso_table.setColumnCount(4)
        self.iso_table.setHorizontalHeaderLabels(["is_used", "Condition", "Temperature", "Color"])
        self.iso_table.setVerticalHeaderLabels([str(i) for i in range(10)])
        roi_list = fetch_all_rois(self.ip, self.user_id, self.user_pw) or [{} for _ in range(10)]

        for i in range(10):
            roi = roi_list[i]
            iso = roi.get("iso", {})
            chk = QCheckBox()
            chk.setChecked(roi.get("used", False))
            chk_widget = QWidget()
            layout = QHBoxLayout(chk_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setAlignment(Qt.AlignCenter)
            layout.addWidget(chk)
            self.iso_table.setCellWidget(i, 0, chk_widget)

            cond_box = QComboBox()
            cond_box.addItems(["above", "below"])
            cond_box.setCurrentText(iso.get("condition", "above"))
            self.iso_table.setCellWidget(i, 1, cond_box)

            temp = QTableWidgetItem(str(iso.get("temperature", "")))
            temp.setTextAlignment(Qt.AlignCenter)
            self.iso_table.setItem(i, 2, temp)

            color_box = QComboBox()
            color_box.addItems(["red", "green", "blue", "grey"])
            color_box.setCurrentText(iso.get("color", "red"))
            self.iso_table.setCellWidget(i, 3, color_box)

        self.iso_table.resizeColumnsToContents()
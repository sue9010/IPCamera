# Camera_Control/correction.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QDoubleSpinBox,
    QCheckBox, QPushButton, QMessageBox
)
import requests

class CorrectionControlPopup(QDialog):
    def __init__(self, ip, user_id, user_pw, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("Correction 설정")
        self.ip = ip
        self.user_id = user_id
        self.user_pw = user_pw

        # ▼ UI 구성
        self.temp_mode = QComboBox()
        self.temp_mode.addItems(["Normal", "High", "Medical", "Medium", "M-High"])
        self.temp_mode_map = {
            "Normal": 1,
            "High": 2,
            "Medical": 4,
            "Medium": 8,
            "M-High": 16
        }

        self.chk_correct = QCheckBox("Correction Enable")

        self.emissivity = QDoubleSpinBox()
        self.emissivity.setRange(0.0, 1.0)
        self.emissivity.setSingleStep(0.01)

        self.transmission = QDoubleSpinBox()
        self.transmission.setRange(0.0, 1.0)
        self.transmission.setSingleStep(0.01)

        self.atmosphere = QDoubleSpinBox()
        self.atmosphere.setRange(-50.0, 100.0)

        self.zero_offset = QDoubleSpinBox()
        self.zero_offset.setRange(-100.0, 100.0)

        self.load_button = QPushButton("불러오기")
        self.load_button.clicked.connect(self.load_settings)

        self.apply_button = QPushButton("적용")
        self.apply_button.clicked.connect(self.apply_settings)

        # ▼ 레이아웃
        form = QFormLayout()
        form.addRow("Temperature Mode", self.temp_mode)
        # form.addRow("Temp Unit", QComboBox())  # 단순 표기용
        form.addRow(self.chk_correct)
        form.addRow("Emissivity", self.emissivity)
        form.addRow("Transmission", self.transmission)
        form.addRow("Atmosphere", self.atmosphere)
        form.addRow("Zero Offset", self.zero_offset)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.load_button)
        layout.addWidget(self.apply_button)
        self.setLayout(layout)

        self.load_settings()

    def load_settings(self):
        url = f"http://{self.ip}/cgi-bin/control/camthermalfunc.cgi"
        params = {
            "id": self.user_id,
            "passwd": self.user_pw,
            "action": "getthermalfunc"
        }
        try:
            resp = requests.get(url, params=params, timeout=3)
            # print("[DEBUG] 응답:\n", resp.text)
            if resp.status_code != 200 or "Error" in resp.text:
                QMessageBox.critical(self, "오류", f"불러오기 실패:\n{resp.text}")
                return

            lines = resp.text.strip().splitlines()
            data = {}
            for line in lines:
                if "=" in line:
                    try:
                        k, v = line.split("=", 1)
                        data[k.strip()] = v.strip()
                    except ValueError:
                        print("[경고] 파싱 실패:", line)

            # ✅ Temperature Mode 리스트 필터링
            support_val = int(data.get("supportmode", "1"))
            MODE_OPTIONS = {
                1: "Normal",
                2: "High",
                4: "Medical",
                8: "Medium",
                16: "M-High"
            }
            supported = [label for bit, label in MODE_OPTIONS.items() if support_val & bit]

            self.temp_mode.clear()
            self.temp_mode.addItems(supported)

            # ✅ 현재 설정된 temp_mode 반영
            raw_mode = data.get("temp_mode", "1").strip().lower()

            reverse_map = {
                "1": "Normal",
                "2": "High",
                "4": "Medical",
                "8": "Medium",
                "16": "M-High",
                "normal": "Normal",
                "high": "High",
                "medical": "Medical",
                "medium": "Medium",
                "m-high": "M-High"
            }
            current = reverse_map.get(raw_mode, "Normal")
            if current in supported:
                self.temp_mode.setCurrentText(current)
            else:
                self.temp_mode.setCurrentIndex(0)  # fallback

            # 나머지 필드
            self.chk_correct.setChecked(data.get("correct_use", "off") == "on")
            self.emissivity.setValue(float(data.get("emissivity", 0.95)))
            self.transmission.setValue(float(data.get("transmission", 1.0)))
            self.atmosphere.setValue(float(data.get("atmosphere", 20.0)))
            self.zero_offset.setValue(float(data.get("zerooffset", 0.0)))

        except Exception as e:
            QMessageBox.critical(self, "예외 발생", str(e))


    def apply_settings(self):
        url = f"http://{self.ip}/cgi-bin/control/camthermalfunc.cgi"
        params = {
            "id": self.user_id,
            "passwd": self.user_pw,
            "action": "setthermalfunc",
            "temp_mode": self.temp_mode_map[self.temp_mode.currentText()],
            "correct_use": "on" if self.chk_correct.isChecked() else "off",
            "emissivity": self.emissivity.value(),
            "transmission": self.transmission.value(),
            "atmosphere": self.atmosphere.value(),
            "zerooffset": self.zero_offset.value()
        }
        try:
            resp = requests.get(url, params=params, timeout=3)
            if resp.status_code == 200 and "Error" not in resp.text:
                self.main_window.log("[설정 변경] Correction")
            else:
                QMessageBox.warning(self, "실패", f"적용 실패:\n{resp.text}")
        except Exception as e:
            QMessageBox.critical(self, "예외 발생", str(e))

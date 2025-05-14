# Camera_Control/image.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QDoubleSpinBox,
    QSpinBox, QCheckBox, QPushButton, QMessageBox
)
import requests

class ImageControlPopup(QDialog):
    def __init__(self, ip, user_id, user_pw, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Control 설정")
        self.ip = ip
        self.user_id = user_id
        self.user_pw = user_pw

        # ▼ UI 요소 생성
        self.color_combo = QComboBox()
        self.color_combo.addItems(["grey", "iron", "rainbow", "greyred", "glowbow", "yellow", "midgrey", "bluered"])

        self.gain_combo = QComboBox()
        self.gain_combo.addItems(["auto", "manual"])

        self.min_gain = QDoubleSpinBox()
        self.min_gain.setRange(1, 16384)

        self.max_gain = QDoubleSpinBox()
        self.max_gain.setRange(1, 16384)

        self.brightness = QSpinBox()
        self.brightness.setRange(-40, 40)

        self.contrast = QSpinBox()
        self.contrast.setRange(-10, 10)

        self.chk_colorinv = QCheckBox("Color Invert")
        self.chk_mirror = QCheckBox("Mirror")
        self.chk_flip = QCheckBox("Flip")

        # ▼ 버튼
        self.load_button = QPushButton("불러오기")
        self.load_button.clicked.connect(self.load_current_settings)

        self.apply_button = QPushButton("적용")
        self.apply_button.clicked.connect(self.apply_settings)

        # ▼ 폼 레이아웃
        form = QFormLayout()
        form.addRow("Color", self.color_combo)
        form.addRow("Gain Control", self.gain_combo)
        form.addRow("Manual Gain min", self.min_gain)
        form.addRow("Manual Gain Max", self.max_gain)
        form.addRow("Brightness", self.brightness)
        form.addRow("Contrast", self.contrast)
        form.addRow(self.chk_colorinv)
        form.addRow(self.chk_mirror)
        form.addRow(self.chk_flip)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.load_button)
        layout.addWidget(self.apply_button)
        self.setLayout(layout)

        # ▼ 팝업 열릴 때 바로 불러오기
        self.load_current_settings()

    def load_current_settings(self):
        url = f"http://{self.ip}/cgi-bin/control/camthermalfunc.cgi"
        params = {
            "id": self.user_id,
            "passwd": self.user_pw,
            "action": "getthermalfunc"
        }
        try:
            resp = requests.get(url, params=params, timeout=3)
            # print("[DEBUG] 응답:\n", resp.text)  # ← 디버깅 로그 추가

            if resp.status_code != 200 or "Error" in resp.text:
                QMessageBox.critical(self, "오류", f"설정 불러오기 실패:\n{resp.text}")
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

            # ✅ 안전하게 개별 파싱
            self.color_combo.setCurrentText(data.get("color", "grey"))
            self.gain_combo.setCurrentText(data.get("gainctrl", "auto"))

            try:
                self.min_gain.setValue(float(data.get("usergainmin", 1)))
            except ValueError:
                pass

            try:
                self.max_gain.setValue(float(data.get("usergainmax", 1)))
            except ValueError:
                pass

            try:
                self.brightness.setValue(int(data.get("bright", 0)))
            except ValueError:
                pass

            try:
                self.contrast.setValue(int(data.get("contrast", 0)))
            except ValueError:
                pass

            self.chk_colorinv.setChecked(data.get("colorinv_use", "off") == "on")
            self.chk_mirror.setChecked(data.get("mirror_use", "off") == "on")
            self.chk_flip.setChecked(data.get("flip_use", "off") == "on")

        except Exception as e:
            QMessageBox.critical(self, "예외 발생", str(e))


    def apply_settings(self):
        url = f"http://{self.ip}/cgi-bin/control/camthermalfunc.cgi"
        params = {
            "id": self.user_id,
            "passwd": self.user_pw,
            "action": "setthermalfunc",
            "color": self.color_combo.currentText(),
            "gainctrl": self.gain_combo.currentText(),
            "usergainmin": int(self.min_gain.value()),
            "usergainmax": int(self.max_gain.value()),
            "bright": int(self.brightness.value()),
            "contrast": int(self.contrast.value()),
            "colorinv_use": "on" if self.chk_colorinv.isChecked() else "off",
            "mirror_use": "on" if self.chk_mirror.isChecked() else "off",
            "flip_use": "on" if self.chk_flip.isChecked() else "off"
        }
        try:
            resp = requests.get(url, params=params, timeout=3)
            if resp.status_code == 200 and "Error" not in resp.text:
                QMessageBox.information(self, "성공", "설정이 적용되었습니다.")
            else:
                QMessageBox.warning(self, "실패", f"설정 적용 실패:\n{resp.text}")
        except Exception as e:
            QMessageBox.critical(self, "예외 발생", str(e))

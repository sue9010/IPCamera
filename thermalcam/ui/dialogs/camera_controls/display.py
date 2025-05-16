# Camera_Control/display.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QCheckBox, QPushButton, QMessageBox
)
import requests

class DisplayControlPopup(QDialog):
    def __init__(self, ip, user_id, user_pw, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("Display 설정")
        self.ip = ip
        self.user_id = user_id
        self.user_pw = user_pw

        # ▼ 체크박스
        self.chk_center = QCheckBox("Show Center")
        self.chk_temp = QCheckBox("Show Temperature")
        self.chk_indicator = QCheckBox("Show Indicator")
        self.chk_colorbar = QCheckBox("Show Color Bar")
 
        # ▼ 버튼
        self.load_button = QPushButton("불러오기")
        self.load_button.clicked.connect(self.load_settings)

        self.apply_button = QPushButton("적용")
        self.apply_button.clicked.connect(self.apply_settings)

        layout = QVBoxLayout()
        layout.addWidget(self.chk_center)
        layout.addWidget(self.chk_temp)
        layout.addWidget(self.chk_indicator)
        layout.addWidget(self.chk_colorbar)
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
            # print("[DEBUG] 응답:\n", resp.text)  # 디버깅
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

            # 필드 반영
            self.chk_center.setChecked(data.get("showcenter_use", "off") == "on")
            self.chk_temp.setChecked(data.get("showtemp_use", "off") == "on")
            self.chk_indicator.setChecked(data.get("showindcator_use", "off") == "on")  # 오타 포함!
            self.chk_colorbar.setChecked(data.get("showcbar_use", "off") == "on")

        except Exception as e:
            QMessageBox.critical(self, "예외 발생", str(e))


    def apply_settings(self):
        url = f"http://{self.ip}/cgi-bin/control/camthermalfunc.cgi"
        params = {
            "id": self.user_id,
            "passwd": self.user_pw,
            "action": "setthermalfunc",
            "showcenter_use": "on" if self.chk_center.isChecked() else "off",
            "showtemp_use": "on" if self.chk_temp.isChecked() else "off",
            "showindcator_use": "on" if self.chk_indicator.isChecked() else "off",
            "showcbar_use": "on" if self.chk_colorbar.isChecked() else "off"
        }
        try:
            resp = requests.get(url, params=params, timeout=3)
            if resp.status_code == 200 and "Error" not in resp.text:
                self.main_window.log("[설정 변경] Display")
            else:
                QMessageBox.warning(self, "실패", f"설정 적용 실패:\n{resp.text}")
        except Exception as e:
            QMessageBox.critical(self, "예외 발생", str(e))

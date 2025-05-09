# Camera_Control/nuc.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QPushButton, QMessageBox
)
import requests

class NUCControlPopup(QDialog):
    def __init__(self, ip, user_id, user_pw, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NUC 설정")
        self.ip = ip
        self.user_id = user_id
        self.user_pw = user_pw

        # ▼ UI 컴포넌트
        self.nuc_mode = QComboBox()
        self.nuc_mode.addItems(["off", "time", "auto", "timeauto"])

        self.nuc_time = QComboBox()
        self.nuc_time.addItems(["0", "60", "120", "180", "240", "300", "600", "1200", "1800", "3600"])

        self.nuc_sens = QComboBox()
        self.nuc_sens.addItems(["lowest", "low", "middle", "high", "highest"])

        self.load_button = QPushButton("불러오기")
        self.load_button.clicked.connect(self.load_settings)

        self.apply_button = QPushButton("적용")
        self.apply_button.clicked.connect(self.apply_settings)

        self.once_button = QPushButton("NUC at Once")
        self.once_button.clicked.connect(self.nuc_once)

        form = QFormLayout()
        form.addRow("NUC", self.nuc_mode)
        form.addRow("NUC Period", self.nuc_time)
        form.addRow("NUC Auto(Sensitivity)", self.nuc_sens)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.load_button)
        layout.addWidget(self.apply_button)
        layout.addWidget(self.once_button)
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

            # ▼ 항목 매핑: 존재하는 값만 반영
            nucmode_val = data.get("nucmode", "off")
            if nucmode_val in [self.nuc_mode.itemText(i) for i in range(self.nuc_mode.count())]:
                self.nuc_mode.setCurrentText(nucmode_val)
            else:
                self.nuc_mode.setCurrentIndex(0)

            nuctime_val = data.get("nuctime", "60")
            if nuctime_val in [self.nuc_time.itemText(i) for i in range(self.nuc_time.count())]:
                self.nuc_time.setCurrentText(nuctime_val)
            else:
                self.nuc_time.setCurrentIndex(1)  # default: 60

            nucsens_val = data.get("nucautosens", "middle")
            if nucsens_val in [self.nuc_sens.itemText(i) for i in range(self.nuc_sens.count())]:
                self.nuc_sens.setCurrentText(nucsens_val)
            else:
                self.nuc_sens.setCurrentIndex(2)  # default: middle

        except Exception as e:
            QMessageBox.critical(self, "예외 발생", str(e))



    def apply_settings(self):
        url = f"http://{self.ip}/cgi-bin/control/camthermalfunc.cgi"
        params = {
            "id": self.user_id,
            "passwd": self.user_pw,
            "action": "setthermalfunc",
            "nucmode": self.nuc_mode.currentText(),
            "nuctime": self.nuc_time.currentText(),
            "nucautosens": self.nuc_sens.currentText()
        }
        try:
            resp = requests.get(url, params=params, timeout=3)
            if resp.status_code == 200 and "Error" not in resp.text:
                QMessageBox.information(self, "성공", "NUC 설정이 적용되었습니다.")
            else:
                QMessageBox.warning(self, "실패", f"NUC 설정 실패:\n{resp.text}")
        except Exception as e:
            QMessageBox.critical(self, "예외 발생", str(e))

    def nuc_once(self):
        url = f"http://{self.ip}/cgi-bin/control/camthermalfunc.cgi"
        params = {
            "id": self.user_id,
            "passwd": self.user_pw,
            "action": "nuc"
        }
        try:
            resp = requests.get(url, params=params, timeout=3)
            if resp.status_code == 200 and "Error" not in resp.text:
                QMessageBox.information(self, "NUC 수행", "NUC가 즉시 실행되었습니다.")
            else:
                QMessageBox.warning(self, "NUC 실패", f"NUC 실행 실패:\n{resp.text}")
        except Exception as e:
            QMessageBox.critical(self, "예외 발생", str(e))

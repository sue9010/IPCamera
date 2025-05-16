from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QPushButton, QMessageBox
)
import requests

class NUCControlPopup(QDialog):
    def __init__(self, ip, user_id, user_pw, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("NUC 설정")
        self.ip = ip
        self.user_id = user_id
        self.user_pw = user_pw

        # ▼ UI 컴포넌트
        self.nuc_mode = QComboBox()
        self.nuc_mode.addItems(["off", "time", "auto", "timeauto"])

        # 초 단위 실제 값
        self.nuc_time_seconds = ["0","60", "120", "180", "240", "300", "600", "1200", "1800", "3600"]
        # UI 표시: 분 단위
        self.nuc_time = QComboBox()
        self.nuc_time_labels = ["OFF" if s == "0" else f"{int(s)//60}분" for s in self.nuc_time_seconds]
        self.nuc_time.addItems(self.nuc_time_labels)

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

            # ▼ nucmode
            nucmode_val = data.get("nucmode", "off")
            # print(f"[디버그] 서버 응답 nucmode 값: {nucmode_val}")
            if nucmode_val in [self.nuc_mode.itemText(i) for i in range(self.nuc_mode.count())]:
                self.nuc_mode.setCurrentText(nucmode_val)
            else:
                self.nuc_mode.setCurrentIndex(0)

            # ▼ nuctime (초 → index 매핑)
            nuctime_val = data.get("nuctime", "60")
            print(f"[디버그] 서버 응답 nuctime 값: {nuctime_val}")
            if nuctime_val in self.nuc_time_seconds:
                index = self.nuc_time_seconds.index(nuctime_val)
                self.nuc_time.setCurrentIndex(index)
            else:
                self.nuc_time.setCurrentIndex(1)  # default: 60s = 1분
 
            # ▼ nucautosens
            nucsens_val = data.get("nucautosens", "middle")
            # print(f"[디버그] 서버 응답 nucautosens 값: {nucsens_val}")
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
            "nuctime": self.nuc_time_seconds[self.nuc_time.currentIndex()],
            "nucautosens": self.nuc_sens.currentText()
        }
        try:
            resp = requests.get(url, params=params, timeout=3)
            if resp.status_code == 200 and "Error" not in resp.text:
                self.main_window.log("[설정 변경] NUC")
            else:
                QMessageBox.warning(self, "실패", f"NUC 설정 실패:\n{resp.text}")
        except Exception as e:
            QMessageBox.critical(self, "예외 발생", str(e))

    def nuc_once(self):
        pass  # TODO: NUC 즉시 실행 기능 추후 구현

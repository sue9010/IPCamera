# Camera_Control/enhancement.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QCheckBox,
    QSpinBox, QPushButton, QMessageBox
)
import requests

class EnhancementControlPopup(QDialog):
    def __init__(self, ip, user_id, user_pw, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("Enhancement 설정")
        self.ip = ip
        self.user_id = user_id
        self.user_pw = user_pw

        # ▼ UI 구성
        self.edge_combo = QComboBox()
        self.edge_combo.addItems(["off", "low", "middle", "high"])

        self.noise_combo = QComboBox()
        self.noise_combo.addItems(["off", "low", "middle", "high"])

        self.chk_imgenhance = QCheckBox("Image Enhancement Type")

        self.chk_clahe = QCheckBox("CLAHE")
        self.chk_cie = QCheckBox("CIE")

        self.cie_weight = QComboBox()
        self.cie_weight.addItems(["lowest", "low", "middle", "high", "highest"])

        self.chk_gamma = QCheckBox("Gamma")

        self.gamma_param1 = QSpinBox()
        self.gamma_param1.setRange(1, 1024)

        self.gamma_param2 = QSpinBox()
        self.gamma_param2.setRange(1, 1024)

        self.load_button = QPushButton("불러오기")
        self.load_button.clicked.connect(self.load_settings)

        self.apply_button = QPushButton("적용")
        self.apply_button.clicked.connect(self.apply_settings)

        form = QFormLayout()
        form.addRow("Edge Enhancement", self.edge_combo)
        form.addRow("Noise Reduction Filter", self.noise_combo)
        form.addRow(self.chk_imgenhance)
        form.addRow(self.chk_clahe)
        form.addRow(self.chk_cie)
        form.addRow("CIE Weight", self.cie_weight)
        form.addRow(self.chk_gamma)
        form.addRow("Gamma Parameter 1", self.gamma_param1)
        form.addRow("Gamma Parameter 2", self.gamma_param2)

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
            if resp.status_code != 200 or "Error" in resp.text:
                QMessageBox.critical(self, "오류", f"불러오기 실패:\n{resp.text}")
                return

            lines = resp.text.strip().splitlines()
            data = {}
            for line in lines:
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()

            # ✅ 각 항목을 안전하게 개별 파싱
            self.edge_combo.setCurrentText(data.get("edgenhance", "off"))
            self.noise_combo.setCurrentText(data.get("noisereducefliter", "off"))
            self.chk_imgenhance.setChecked(data.get("imgenhance_use", "off") == "on")
            self.chk_clahe.setChecked(data.get("imgAHE", "off") == "on")
            self.chk_cie.setChecked(data.get("imgCIE", "off") == "on")
            self.cie_weight.setCurrentText(data.get("imgweightcie", "lowest"))
            self.chk_gamma.setChecked(data.get("gamma_use", "off") == "on")
 
            try:
                self.gamma_param1.setValue(int(data.get("gamma_param1", 256)))
            except ValueError:
                pass
            try:
                self.gamma_param2.setValue(int(data.get("gamma_param2", 768)))
            except ValueError:
                pass

        except Exception as e:
            QMessageBox.critical(self, "예외 발생", str(e))


    def apply_settings(self):
        url = f"http://{self.ip}/cgi-bin/control/camthermalfunc.cgi"
        params = {
            "id": self.user_id,
            "passwd": self.user_pw,
            "action": "setthermalfunc",
            "edgenhance": self.edge_combo.currentText(),
            "noisereducefliter": self.noise_combo.currentText(),
            "imgenhance_use": "on" if self.chk_imgenhance.isChecked() else "off",
            "imgAHE": "on" if self.chk_clahe.isChecked() else "off",
            "imgCIE": "on" if self.chk_cie.isChecked() else "off",
            "imgweightcie": self.cie_weight.currentText(),
            "gamma_use": "on" if self.chk_gamma.isChecked() else "off",
            "gamma_param1": self.gamma_param1.value(),
            "gamma_param2": self.gamma_param2.value()
        }
        try:
            resp = requests.get(url, params=params, timeout=3)
            if resp.status_code == 200 and "Error" not in resp.text:
                self.main_window.log("[설정 변경] Enhancement")
            else:
                QMessageBox.warning(self, "실패", f"적용 실패:\n{resp.text}")
        except Exception as e:
            QMessageBox.critical(self, "예외 발생", str(e))

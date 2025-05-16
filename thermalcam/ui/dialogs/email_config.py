# thermalcam/ui/dialogs/email_config.py

from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5 import uic
import importlib.resources
import json
import os

CONFIG_PATH = os.path.expanduser("~/.thermal_email_config.json")
 
class EmailConfigPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        with importlib.resources.path("thermalcam.resources.ui", "email_config.ui") as ui_path:
            uic.loadUi(str(ui_path), self)

        self.load_config()

        self.saveButton.clicked.connect(self.save_config)
        self.cancelButton.clicked.connect(self.reject)

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
                self.smtpServerInput.setText(data.get("smtp_server", "smtp.gmail.com"))
                self.smtpPortInput.setText(str(data.get("smtp_port", 587)))
                self.senderEmailInput.setText(data.get("sender_email", ""))
                self.senderPasswordInput.setText(data.get("sender_password", ""))
                self.recipientEmailInput.setText(data.get("recipient_email", ""))

    def save_config(self):
        data = {
            "smtp_server": self.smtpServerInput.text().strip(),
            "smtp_port": int(self.smtpPortInput.text().strip()),
            "sender_email": self.senderEmailInput.text().strip(),
            "sender_password": self.senderPasswordInput.text().strip(),
            "recipient_email": self.recipientEmailInput.text().strip(),
        }
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=2)

        QMessageBox.information(self, "저장 완료", "이메일 설정이 저장되었습니다.")
        self.accept()

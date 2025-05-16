# thermalcam/ui/alarm_handlers.py

import smtplib
from email.mime.text import MIMEText
from PyQt5.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QApplication
from PyQt5.QtMultimedia import QSound
import os
import json

CONFIG_PATH = os.path.expanduser("~/.thermal_email_config.json")

def show_popup(message: str, main_window=None):
    """경고 메시지를 띄우고 알람 정지 버튼을 포함한 팝업 표시"""
    dialog = QDialog()
    dialog.setWindowTitle("🔔 온도 경고 발생")

    layout = QVBoxLayout()
    label = QLabel(message)
    stop_button = QPushButton("🔕 알람 정지")

    layout.addWidget(label)
    layout.addWidget(stop_button)
    dialog.setLayout(layout)

    def stop_alarm():
        if main_window is not None and hasattr(main_window, "popupAlarmButton"):
            main_window.popupAlarmButton.setChecked(False)
            main_window.alarm_settings["popup"] = False
            main_window.log("🔕 팝업 알람 수동 해제됨")
        dialog.accept()

    stop_button.clicked.connect(stop_alarm)
    dialog.exec_()

def play_sound():
    try:
        QSound.play("thermalcam/resources/sound/alarm.wav")
    except Exception as e:
        print(f"[사운드 알람 오류] {e}")

def send_email(subject: str, body: str, main_window=None):
    if not os.path.exists(CONFIG_PATH):
        print("[이메일 알람] 설정 파일이 없습니다.")
        return

    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)

        smtp_server = config.get("smtp_server")
        smtp_port = int(config.get("smtp_port", 587))
        sender_email = config.get("sender_email")
        sender_pw = config.get("sender_password")
        recipient_email = config.get("recipient_email")

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient_email

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_pw)
            server.send_message(msg)

        if main_window is not None and hasattr(main_window, "log"):
            main_window.log("📧 이메일 알람 전송 완료")

    except Exception as e:
        print("[이메일 전송 실패]")
        print(e)

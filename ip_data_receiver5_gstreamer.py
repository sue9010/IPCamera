import sys
import cv2
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QMessageBox
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer

class OpenCVViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RTSP Viewer (GStreamer)")
        self.setGeometry(100, 100, 800, 600)

        # 라벨 (영상 출력용)
        self.label = QLabel(self)
        self.label.setFixedSize(640, 480)

        # 입력창 및 버튼
        self.ip_input = QLineEdit("192.168.0.56")
        self.port_input = QLineEdit("554")
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")

        self.start_button.clicked.connect(self.start_stream)
        self.stop_button.clicked.connect(self.stop_stream)

        # 레이아웃 구성
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("IP:"))
        control_layout.addWidget(self.ip_input)
        control_layout.addWidget(QLabel("Port:"))
        control_layout.addWidget(self.port_input)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)

        layout = QVBoxLayout()
        layout.addLayout(control_layout)
        layout.addWidget(self.label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 타이머 및 VideoCapture
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.cap = None
        self.reconnect_attempts = 0
        self.max_reconnect = 3

    def create_gst_pipeline(self, ip, port):
        """GStreamer 파이프라인 문자열 생성"""
        rtsp_url = f"rtsp://{ip}:{port}/stream1"
        return (
            f'rtspsrc location={rtsp_url} latency=0 ! '
            'rtph264depay ! h264parse ! '
            'avdec_h264 ! '
            'videoconvert ! '
            'video/x-raw,format=BGR ! '
            'appsink drop=true sync=false'
        )

    def start_stream(self):
        """GStreamer를 사용하여 RTSP 스트림 시작"""
        self.reconnect_attempts = 0
        ip = self.ip_input.text().strip()
        port = self.port_input.text().strip()
        
        # GStreamer 파이프라인 생성
        pipeline = self.create_gst_pipeline(ip, port)
        print(f"[INFO] 파이프라인: {pipeline}")
        
        if self.cap:
            self.cap.release()
        
        # GStreamer 백엔드 사용
        self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        
        if not self.cap.isOpened():
            QMessageBox.critical(self, "오류", "GStreamer 스트림 연결 실패!\n경로와 네트워크를 확인하세요.")
            print("[ERROR] GStreamer 스트림 연결 실패")
            return
            
        print(f"[INFO] 연결 성공: rtsp://{ip}:{port}/stream1")
        self.timer.start(33)  # 약 30 FPS

    def stop_stream(self):
        """스트림 중지"""
        if self.cap:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.label.clear()
            print("[INFO] 스트림 중지됨.")

    def update_frame(self):
        """프레임 업데이트 (오류 처리 강화)"""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            
            if not ret:
                # 프레임 읽기 실패 시 재연결 시도
                self.reconnect_attempts += 1
                print(f"[WARNING] 프레임 읽기 오류 (시도 {self.reconnect_attempts}/{self.max_reconnect})")
                
                if self.reconnect_attempts >= self.max_reconnect:
                    print("[ERROR] 최대 재연결 시도 횟수 초과")
                    self.stop_stream()
                return
                
            # 성공적으로 프레임을 읽었으면 카운터 리셋
            self.reconnect_attempts = 0
            
            # 프레임 처리 및 표시
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            qimg = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
            self.label.setPixmap(QPixmap.fromImage(qimg))

    def closeEvent(self, event):
        """앱 종료 시 정리"""
        self.stop_stream()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = OpenCVViewer()
    viewer.show()
    sys.exit(app.exec_())

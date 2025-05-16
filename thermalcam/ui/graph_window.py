import sys
import json
import socket
import threading
import time
from collections import deque, defaultdict

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox, QScrollBar
)
from PyQt5.QtCore import QTimer, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from thermalcam.core.camera_client import ThermalReceiver

TARGET_PORT = 60110
MAX_SECONDS = 1800
TEMP_MIN = -30
TEMP_MAX = 130
SAMPLING_INTERVAL = 1.0  # seconds
WINDOW_DURATION = 60  # seconds


class GraphCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 6))
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
 
        self.ax.set_xlim(0, WINDOW_DURATION)
        self.ax.set_ylim(TEMP_MIN, TEMP_MAX)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Temperature (℃)")
        self.ax.set_title("Real-time Max Temperature per ROI")

        self.lines = {}
        for i in range(10):
            line, = self.ax.plot([], [], label=f"area{i}")
            self.lines[i] = line

        self.ax.legend(loc="upper left", bbox_to_anchor=(0, 1))
        self.ax.grid(True)

        self.data = defaultdict(lambda: deque(maxlen=int(MAX_SECONDS / SAMPLING_INTERVAL)))
        self.time = deque(maxlen=int(MAX_SECONDS / SAMPLING_INTERVAL))

        self.view_start = 0
        self.auto_follow = True
        self.scrollbar = None

        # 확대 드래그 변수
        self._dragging = False
        self._drag_start = None
        self._drag_end = None
        self._highlight = None

        self.mpl_connect("button_press_event", self.on_press)
        self.mpl_connect("motion_notify_event", self.on_motion)
        self.mpl_connect("button_release_event", self.on_release)

    def set_view_start(self, value):
        if self.scrollbar and value == self.scrollbar.maximum():
            self.auto_follow = True
        else:
            self.auto_follow = False
        self.view_start = value

    def update_plot(self):
        current_time = len(self.time)
        points_per_window = int(WINDOW_DURATION / SAMPLING_INTERVAL)
        if current_time <= points_per_window:
            window_start = 0
            window_end = points_per_window
        else:
            if self.auto_follow:
                self.view_start = current_time - points_per_window
            window_start = self.view_start
            window_end = min(self.view_start + points_per_window, current_time)

        for i in range(10):
            full_y_data = list(self.data[i])
            full_x_data = list(self.time)
            y_data = full_y_data[window_start:window_end]
            x_data = full_x_data[window_start:window_end]
            self.lines[i].set_data(x_data, y_data)

        if x_data:
            self.ax.set_xlim(x_data[0], x_data[-1])
        else:
            self.ax.set_xlim(0, WINDOW_DURATION)
        self.draw()

    def on_press(self, event):
        if event.dblclick and event.inaxes == self.ax:
            self.auto_follow = True
            return
        if event.button == 1 and event.inaxes == self.ax:
            self._dragging = True
            self._drag_start = event.xdata

    def on_motion(self, event):
        if self._dragging and event.inaxes == self.ax:
            self._drag_end = event.xdata
            x1, x2 = sorted([self._drag_start, self._drag_end])
            if self._highlight:
                self._highlight.remove()
            self._highlight = self.ax.axvspan(x1, x2, color='gray', alpha=0.3)
            self.draw()

    def on_release(self, event):
        if self._highlight:
            self._highlight.remove()
            self._highlight = None
        if self._dragging and self._drag_start is not None and self._drag_end is not None:
            x1, x2 = sorted([self._drag_start, self._drag_end])
            if abs(x2 - x1) >= 1:
                self.ax.set_xlim(x1, x2)
                self.auto_follow = False
                self.draw()
        self._dragging = False
        self._drag_start = None
        self._drag_end = None


class GraphWindow(QMainWindow):
    def __init__(self, ip_address):
        super().__init__()
        self.setWindowTitle("Thermal Graph Viewer")
        self.setGeometry(100, 100, 960, 540)

        self.canvas = GraphCanvas(self)
        self.scrollbar = QScrollBar(Qt.Horizontal)
        self.scrollbar.setMinimum(0)
        self.scrollbar.setMaximum(int(MAX_SECONDS / SAMPLING_INTERVAL) - int(WINDOW_DURATION / SAMPLING_INTERVAL))
        self.scrollbar.setPageStep(1)
        self.scrollbar.valueChanged.connect(self.handle_scrollbar_change)
        self.canvas.scrollbar = self.scrollbar

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.scrollbar)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.thermal_data = {}
        self.receiver = ThermalReceiver(ip_address, TARGET_PORT, self.thermal_data)
        self.receiver.start()

        self.start_time = time.time()
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_graph)
        self.timer.start(int(SAMPLING_INTERVAL * 1000))

    def handle_scrollbar_change(self, value):
        self.canvas.set_view_start(value)

    def refresh_graph(self):
        t = round(time.time() - self.start_time, 1)
        self.canvas.time.append(t)
        for i in range(10):
            max_temp = self.thermal_data.get(i, {}).get("max")
            self.canvas.data[i].append(max_temp if max_temp is not None else None)

        current_point = len(self.canvas.time)
        points_per_window = int(WINDOW_DURATION / SAMPLING_INTERVAL)
        if current_point > points_per_window:
            self.scrollbar.setMaximum(max(0, current_point - points_per_window))
            self.scrollbar.setEnabled(True)
            if self.canvas.auto_follow:
                self.scrollbar.setValue(current_point - points_per_window)
        else:
            self.scrollbar.setEnabled(False)

        self.canvas.update_plot()

    def show_disconnected_alert(self):
        QMessageBox.critical(self, "연결 끊기면", "장비와의 연결이 끊기였습니다. 3회 재시도 실패")

    def closeEvent(self, event):
        if self.receiver:
            self.receiver.stop()
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = GraphWindow("192.168.0.56")
    win.show()
    sys.exit(app.exec_())
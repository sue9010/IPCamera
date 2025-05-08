# ip_selector_popup.py
from PyQt5.QtWidgets import QDialog, QListWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import socket
import concurrent.futures
import psutil


def check_port(ip, port, timeout=0.5):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except:
        return False


def get_local_subnet_ips():
    candidates = set()
    for iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip = addr.address
                try:
                    base = ip.rsplit('.', 1)[0]
                    for i in range(1, 255):
                        candidates.add(f"{base}.{i}")
                except:
                    continue
    return sorted(candidates)


class ScanWorker(QThread):
    result_ready = pyqtSignal(list)

    def run(self):
        all_ips = get_local_subnet_ips()
        valid_ips = []

        def check(ip):
            return ip if check_port(ip, 60110) else None

        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            results = executor.map(check, all_ips)
        for ip in results:
            if ip:
                valid_ips.append(ip)

        self.result_ready.emit(valid_ips)


class IPSelectorPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("열화상 카메라 IP 검색")
        self.resize(300, 400)

        self.label = QLabel("검색 중...")
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

        self.list_widget.itemDoubleClicked.connect(self.handle_double_click)

        self.worker = ScanWorker()
        self.worker.result_ready.connect(self.display_results)
        self.worker.start()

    def display_results(self, ips):
        self.label.setText("검색 결과")
        self.list_widget.clear()
        if not ips:
            self.list_widget.addItem("검색된 장비 없음")
        else:
            for ip in ips:
                self.list_widget.addItem(ip)

    def handle_double_click(self, item):
        ip = item.text()
        if ip and ip.count('.') == 3:
            self.accept()
            self.selected_ip = ip
        else:
            self.selected_ip = None

    def get_selected_ip(self):
        return getattr(self, 'selected_ip', None)
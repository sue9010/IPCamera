# focus_control.py
import threading
import requests
import time
 
class FocusController:
    def __init__(self, get_ip_func, get_speed_func, user_id='admin', password='admin'):
        self.get_ip = get_ip_func
        self.get_speed = get_speed_func
        self.user_id = user_id
        self.password = password
        self.running = False
        self.thread = None

    def _send_focus_command(self, direction):
        ip = self.get_ip()
        speed = self.get_speed()
        url = f"http://{ip}/cgi-bin/control/zf_control.cgi"
        params = {
            "id": self.user_id,
            "passwd": self.password,
            "action": "setzfmove",
            "focus": direction,
            "focusspeed": speed
        }
        try:
            requests.get(url, params=params, timeout=1)
        except Exception as e:
            print(f"[FocusController] Failed to send {direction} command: {e}")

    def start_focus(self, direction):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._focus_loop, args=(direction,), daemon=True)
        self.thread.start()

    def _focus_loop(self, direction):
        while self.running:
            self._send_focus_command(direction)
            time.sleep(0.2)  # 200ms 간격

    def stop_focus(self):
        self.running = False
        if self.thread:
            self.thread.join()
            self._send_focus_command("stop")

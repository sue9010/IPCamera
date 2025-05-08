import socket
import threading
import json
import time

class ThermalReceiver(threading.Thread):
    def __init__(self, host, port, data_store):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.data_store = data_store  # area_id -> {온도 + 좌표 포함}
        self.running = False

    def run(self):
        self.running = True
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.host, self.port))
                s.settimeout(None)
                print(f"[ThermalReceiver] Connected to {self.host}:{self.port}")

                while self.running:
                    data = s.recv(4096)
                    if not data:
                        break
                    try:
                        decoded = data.decode('utf-8').strip()
                        if decoded.startswith('[') and not decoded.endswith(']'):
                            decoded += ']'
                        json_data = json.loads(decoded)
                        for item in json_data:
                            area_id = item.get("area_id")
                            if area_id is not None:
                                self.data_store[area_id] = {
                                    "max": item.get("temp_max", "-"),
                                    "min": item.get("temp_min", "-"),
                                    "avr": item.get("temp_avr", "-"),
                                    "point_max_x": item.get("point_max_x"),
                                    "point_max_y": item.get("point_max_y"),
                                    "point_min_x": item.get("point_min_x"),
                                    "point_min_y": item.get("point_min_y")
                                }
                    except Exception as e:
                        print(f"[ThermalReceiver] Parse error: {e}")
                        continue
        except Exception as e:
            print(f"[ThermalReceiver] Connection error: {e}")

    def stop(self):
        self.running = False

import socket
import threading
import json
from thermalcam.core.alarm import evaluate_alarms

class ThermalReceiver(threading.Thread):
    def __init__(self, host, port, data_store, on_roi_refresh=None, roi_data=None):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.data_store = data_store
        self.running = False
        self.on_roi_refresh = on_roi_refresh
        self.rois = roi_data or []  # ✅ 알람 조건 보관용

    def run(self):
        self.running = True
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.host, self.port))
                s.settimeout(None)

                while self.running:
                    data = s.recv(4096)
                    if not data:
                        break
                    try:
                        decoded = data.decode('utf-8').strip()

                        # 여러 JSON 배열이 붙어있는 경우 처리
                        chunks = decoded.replace('][', ']|[').split('|')

                        for chunk in chunks:
                            try:
                                json_data = json.loads(chunk)

                                for item in json_data:
                                    area_id = item.get("area_id")
                                    if area_id == 100 and self.on_roi_refresh:
                                        self.on_roi_refresh()
                                    elif area_id is not None:
                                        self.data_store[area_id] = {
                                            "max": item.get("temp_max", "-"),
                                            "min": item.get("temp_min", "-"),
                                            "avr": item.get("temp_avr", "-"),
                                            "point_max_x": item.get("point_max_x"),
                                            "point_max_y": item.get("point_max_y"),
                                            "point_min_x": item.get("point_min_x"),
                                            "point_min_y": item.get("point_min_y")
                                        }

                                # 알람 조건 평가
                                if self.rois:
                                    evaluate_alarms(self.rois, self.data_store)

                            except Exception as e:
                                print(f"[ThermalReceiver] JSON parse error: {e}")

                    except Exception as e:
                        print(f"[ThermalReceiver] Decode error: {e}")
        except Exception as e:
            print(f"[ThermalReceiver] Connection error: {e}")


    def stop(self):
        self.running = False

# roi_utils.py
import requests
import json
import re
import os
import cv2

def fetch_all_rois(ip):
    rois = []
    try:
        for i in range(10):
            url = f"http://{ip}/cgi-bin/control/camthermalroi.cgi"
            params = {
                "id": "admin",
                "passwd": "admin",
                "action": f"getthermalroi{i}"
            }
            resp = requests.get(url, params=params, timeout=2)
            if resp.status_code == 200:
                lines = resp.text.strip().splitlines()
                data = {
                    k.strip(): v.strip()
                    for line in lines if "=" in line
                    for k, v in [line.split("=", 1)]
                }
                if data.get("roi_use") == "on":
                    try:
                        sx = int(data["startx"])
                        sy = int(data["starty"])
                        ex = int(data["endx"])
                        ey = int(data["endy"])
                        rois.append((sx, sy, ex, ey))
                    except Exception:
                        continue
    except Exception:
        pass
    return rois


def draw_rois(frame, rois, thermal_data=None, scale_x=1.0, scale_y=1.0):
    for idx, (sx, sy, ex, ey) in enumerate(rois):
        # Scale ROI coordinates
        sx_r, sy_r, ex_r, ey_r = map(lambda v: int(v[0] * v[1]), zip((sx, sy, ex, ey), (scale_x, scale_y, scale_x, scale_y)))

        # Draw rectangle
        cv2.rectangle(frame, (sx_r, sy_r), (ex_r, ey_r), (0, 255, 0), 1)

        # Label position
        label_pos = (sx_r + 2, sy_r - 5 if sy_r - 5 > 0 else sy_r + 12)
        cv2.putText(
            frame,
            f"ROI{idx}",
            label_pos,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.3,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

        # 🔴 draw max/min points if available
        if thermal_data and idx in thermal_data:
            td = thermal_data[idx]

            # max point (빨간색)
            if td.get("point_max_x") is not None and td.get("point_max_y") is not None:
                x_max = int(td["point_max_x"] * scale_x)
                y_max = int(td["point_max_y"] * scale_y)
                cv2.rectangle(frame, (x_max, y_max), (x_max + 4, y_max + 4), (255, 0, 0), -1)

            # min point (파란색)
            if td.get("point_min_x") is not None and td.get("point_min_y") is not None:
                x_min = int(td["point_min_x"] * scale_x)
                y_min = int(td["point_min_y"] * scale_y)
                cv2.rectangle(frame, (x_min, y_min), (x_min + 4, y_min + 4), (0, 0, 255), -1)


def load_latest_roi_temps(file_path='thermal_camera_data.txt'):
    results = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        matches = re.findall(r'\[\s*{.*?}\s*\]', content, re.DOTALL)
        if not matches:
            return results
        last_block = matches[-1]
        data_list = json.loads(last_block)
        for entry in data_list:
            area_id = entry.get("area_id")
            if area_id is not None:
                results[area_id] = {
                    "max": entry.get("temp_max", "-"),
                    "min": entry.get("temp_min", "-"),
                    "avr": entry.get("temp_avr", "-")
                }
    except Exception:
        pass
    return results
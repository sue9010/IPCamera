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


def draw_rois(frame, rois, thermal_data=None):
    for idx, (sx, sy, ex, ey) in enumerate(rois):
        # Draw rectangle
        cv2.rectangle(frame, (sx, sy), (ex, ey), (255, 0, 0), 2)
        # Label position
        label_pos = (sx + 2, sy - 5 if sy - 5 > 0 else sy + 12)
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
# roi_utils.py
import requests
import json
import re
import os
import cv2

def fetch_all_rois(ip, user_id, user_pw):
    rois = []
    try:
        for i in range(10):
            url = f"http://{ip}/cgi-bin/control/camthermalroi.cgi"
            params = {
                "id": user_id,
                "passwd": user_pw,
                "action": f"getthermalroi{i}"
            }
            resp = requests.get(url, params=params, timeout=2)

            if resp.status_code != 200 or "Unauthorized" in resp.text:
                return None

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

                    alarm_data = {
                        "alarm_use": data.get("alarm_use"),
                        "mode": data.get("mode"),
                        "condition": data.get("condition"),
                        "temperature": data.get("temperature"),
                        "start_delay": data.get("start_delay"),
                        "stop_delay": data.get("stop_delay")
                    }

                    rois.append({
                        "coords": (sx, sy, ex, ey),
                        "alarm": alarm_data
                    })
                except Exception:
                    continue
    except Exception:
        return None
    return rois


def draw_rois(frame, rois, thermal_data=None, scale_x=1.0, scale_y=1.0):
    for idx, roi in enumerate(rois):
        if isinstance(roi, dict):
            sx, sy, ex, ey = roi["coords"]
        else:
            sx, sy, ex, ey = roi

        sx_r, sy_r, ex_r, ey_r = map(lambda v: int(v[0] * v[1]), zip((sx, sy, ex, ey), (scale_x, scale_y, scale_x, scale_y)))

        cv2.rectangle(frame, (sx_r, sy_r), (ex_r, ey_r), (0, 255, 0), 1)

        label_pos = (ex_r - 35, ey_r - 5)
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

        if thermal_data and idx in thermal_data:
            td = thermal_data[idx]
            temp_lines = [
                f"Max: {td['max']}",
                f"Min: {td['min']}",
                f"Avg: {td['avr']}"
            ]
            font_scale = 0.4
            line_height = int(35 * font_scale)

            for i, line in enumerate(temp_lines):
                cv2.putText(
                    frame,
                    line,
                    (sx_r + 3, sy_r + 15 + i * line_height),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA
                )

            if td.get("point_min_x") is not None and td.get("point_min_y") is not None:
                x_max = int(td["point_min_x"] * scale_x)
                y_max = int(td["point_min_y"] * scale_y)
                cv2.rectangle(frame, (x_max, y_max), (x_max + 4, y_max + 4), (0, 0, 255), -1)

            if td.get("point_max_x") is not None and td.get("point_max_y") is not None:
                x_min = int(td["point_max_x"] * scale_x)
                y_min = int(td["point_max_y"] * scale_y)
                cv2.rectangle(frame, (x_min, y_min), (x_min + 4, y_min + 4), (255, 0, 0), -1)

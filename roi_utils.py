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
            
            # 로그인 실패 or 기타 오류 응답
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
                    rois.append((sx, sy, ex, ey))
                except Exception:
                    continue
    except Exception:
        return None
    return rois



def draw_rois(frame, rois, thermal_data=None, scale_x=1.0, scale_y=1.0):
    for idx, (sx, sy, ex, ey) in enumerate(rois):
        # Scale ROI coordinates
        sx_r, sy_r, ex_r, ey_r = map(lambda v: int(v[0] * v[1]), zip((sx, sy, ex, ey), (scale_x, scale_y, scale_x, scale_y)))

        # Draw rectangle
        cv2.rectangle(frame, (sx_r, sy_r), (ex_r, ey_r), (0, 255, 0), 1)

        # Label position (우측 하단 내부)
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

        # 🔴 draw max/min points if available
        if thermal_data and idx in thermal_data:
            td = thermal_data[idx]

            # 온도 텍스트 (좌측 상단 내부)
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

            # 원래 min 위치가 사실 max임 → 빨간색
            if td.get("point_min_x") is not None and td.get("point_min_y") is not None:
                x_max = int(td["point_min_x"] * scale_x)
                y_max = int(td["point_min_y"] * scale_y)
                cv2.rectangle(frame, (x_max, y_max), (x_max + 4, y_max + 4), (0, 0, 255), -1)  # 🔴

            # 원래 max 위치가 사실 min임 → 파란색
            if td.get("point_max_x") is not None and td.get("point_max_y") is not None:
                x_min = int(td["point_max_x"] * scale_x)
                y_min = int(td["point_max_y"] * scale_y)
                cv2.rectangle(frame, (x_min, y_min), (x_min + 4, y_min + 4), (255, 0, 0), -1)  # 🔵
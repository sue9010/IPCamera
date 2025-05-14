# roi_utils.py
import requests
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

            roi_use = data.get("roi_use", "off") == "on"
            try:
                sx = int(data.get("startx", 0))
                sy = int(data.get("starty", 0))
                ex = int(data.get("endx", 0))
                ey = int(data.get("endy", 0))
            except Exception as e:
                print(f"[ROI {i}] 좌표 파싱 실패: {e}")
                sx = sy = ex = ey = 0

            alarm_data = {
                "alarm_use": data.get("alarm_use", "off"),
                "mode": data.get("mode", ""),
                "condition": data.get("condition", ""),
                "temperature": data.get("temperature", ""),
                "start_delay": data.get("start_delay", ""),
                "stop_delay": data.get("stop_delay", ""),
                "alarm_out": data.get("alarm_out", "")
            }

            iso_data = {
                "iso_use": data.get("iso_use", "off"),
                "condition": data.get("condition", ""),
                "temperature": data.get("temperature", ""),
                "color": data.get("iso_color", "")
            }

            rois.append({
                "coords": (sx, sy, ex, ey),
                "used": roi_use,
                "alarm": alarm_data,
                "iso": iso_data
            })
    except Exception as e:
        print(f"[fetch_all_rois] 예외 발생: {e}")
        return None
    return rois





def draw_rois(frame, rois, thermal_data=None, scale_x=1.0, scale_y=1.0):
    for idx, roi in enumerate(rois):
        # ✅ 사용하지 않는 ROI는 건너뜀
        if isinstance(roi, dict) and roi.get("used") is False:
            continue

        if isinstance(roi, dict):
            sx, sy, ex, ey = roi["coords"]
            alarm = roi.get("alarm", {})
        else:
            sx, sy, ex, ey = roi
            alarm = {}

        sx_r, sy_r, ex_r, ey_r = map(lambda v: int(v[0] * v[1]), zip((sx, sy, ex, ey), (scale_x, scale_y, scale_x, scale_y)))

        # 알람 유무 판단
        alert_triggered = False
        if thermal_data and idx in thermal_data and isinstance(roi, dict):
            td = thermal_data[idx]
            if alarm.get("alarm_use") == "on" and alarm.get("condition") in ("above", "below") and alarm.get("temperature"):
                try:
                    threshold = float(alarm["temperature"])
                    mode = alarm.get("mode", "maximum")
                    key = {"maximum": "max", "minimum": "min", "average": "avr"}.get(mode)
                    if key and key in td:
                        temp = float(td[key])
                        if (alarm["condition"] == "above" and temp > threshold) or \
                           (alarm["condition"] == "below" and temp < threshold):
                            alert_triggered = True
                except:
                    pass

        # 알람 경고 채워진 테두리
        if alert_triggered:
            overlay = frame.copy()
            cv2.rectangle(overlay, (sx_r, sy_r), (ex_r, ey_r), (255, 0, 0), -1)
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

        # 테두리
        cv2.rectangle(frame, (sx_r, sy_r), (ex_r, ey_r), (0, 255, 0), 1)

        # ROI 이름 표시 (우측 상단)
        label_pos = (ex_r - 25, sy_r + 15)
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

        # 업데이트 데이터
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
                cv2.rectangle(frame, (x_max, y_max), (x_max + 4, y_max + 4), (255, 0, 0), -1)

            if td.get("point_max_x") is not None and td.get("point_max_y") is not None:
                x_min = int(td["point_max_x"] * scale_x)
                y_min = int(td["point_max_y"] * scale_y)
                cv2.rectangle(frame, (x_min, y_min), (x_min + 4, y_min + 4), (0, 0, 255), -1)

            # ✅ 사용자 알람 조건 영어로 표시
            if alarm.get("alarm_use") == "on":
                mode_map = {"maximum": "Max", "minimum": "Min", "average": "Avg"}
                m = mode_map.get(alarm.get("mode"), "")
                op = ">" if alarm.get("condition") == "above" else "<"
                t = alarm.get("temperature", "")
                if m and op and t:
                    text = f"{m} {op} {t}"
                    cv2.putText(
                        frame,
                        text,
                        (sx_r + 3, ey_r - 5),  # 좌측 하단
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.35,
                        (255, 255, 0),
                        1,
                        cv2.LINE_AA
                    )

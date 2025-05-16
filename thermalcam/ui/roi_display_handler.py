# thermalcam/ui/roi_display_handler.py

from PyQt5.QtWidgets import QLabel
from thermalcam.core.roi import draw_rois
from thermalcam.core.roi import fetch_all_rois
from thermalcam.core.alarm import fetch_alarm_conditions


def init_roi_labels(viewer):
    """ROI 라벨 그리드 초기화"""
    grid_layout = viewer.roi_grid.layout()
    grid_layout.addWidget(QLabel("영역"), 0, 0)
    grid_layout.addWidget(QLabel("Max"), 0, 1)
    grid_layout.addWidget(QLabel("Min"), 0, 2)
    grid_layout.addWidget(QLabel("Avg"), 0, 3)

    viewer.roi_label_matrix = []

    for i in range(10):
        max_lbl = QLabel("-")
        min_lbl = QLabel("-")
        avr_lbl = QLabel("-")
        grid_layout.addWidget(QLabel(f"ROI{i}"), i + 1, 0)
        grid_layout.addWidget(max_lbl, i + 1, 1)
        grid_layout.addWidget(min_lbl, i + 1, 2)
        grid_layout.addWidget(avr_lbl, i + 1, 3)
        viewer.roi_label_matrix.append({
            "max": max_lbl,
            "min": min_lbl,
            "avr": avr_lbl
        })

def process_roi_display(viewer, rgb, scale_x, scale_y):
    """ROI 데이터 표시 및 알람 시각화"""
    alarming_map = {i: [] for i in range(10)}
    mode_map = {"maximum": "max", "minimum": "min", "average": "avr"}

    for i in range(10):
        roi = viewer.rois[i] if i < len(viewer.rois) else None
        td = viewer.thermal_data.get(i)
        if not roi or not td:
            continue

        alarm = roi.get("alarm", {})
        if alarm.get("alarm_use") == "on" and alarm.get("condition") in ("above", "below") and alarm.get("temperature"):
            try:
                threshold = float(alarm["temperature"])
                mode = alarm.get("mode", "maximum")
                key = mode_map.get(mode)
                if key and key in td:
                    temp = float(td[key])
                    if (alarm["condition"] == "above" and temp > threshold) or \
                       (alarm["condition"] == "below" and temp < threshold):
                        alarming_map[i].append(key)
            except:
                continue

    if viewer.should_draw_rois and any(isinstance(roi, dict) and roi.get("used") for roi in viewer.rois):
        draw_rois(rgb, viewer.rois, viewer.thermal_data, scale_x, scale_y)

    else:
        pass

    for i in range(10):
        temp = viewer.thermal_data.get(i)
        alerts = alarming_map.get(i, [])
        if temp:
            viewer.roi_label_matrix[i]["max"].setText(f"{temp['max']}℃")
            viewer.roi_label_matrix[i]["min"].setText(f"{temp['min']}℃")
            viewer.roi_label_matrix[i]["avr"].setText(f"{temp['avr']}℃")
        else:
            viewer.roi_label_matrix[i]["max"].setText("-")
            viewer.roi_label_matrix[i]["min"].setText("-")
            viewer.roi_label_matrix[i]["avr"].setText("-")

        viewer.roi_label_matrix[i]["max"].setStyleSheet("background-color: rgb(255, 128, 128);" if "max" in alerts else "")
        viewer.roi_label_matrix[i]["min"].setStyleSheet("background-color: rgb(255, 128, 128);" if "min" in alerts else "")
        viewer.roi_label_matrix[i]["avr"].setStyleSheet("background-color: rgb(255, 128, 128);" if "avr" in alerts else "")

def refresh_rois(viewer):
    ip = viewer.ip_input.text().strip()
    user_id = viewer.id_input.text().strip()
    user_pw = viewer.pw_input.text().strip()
    viewer.rois = fetch_all_rois(ip, user_id, user_pw)
    viewer.roi_alarm_config = fetch_alarm_conditions(ip, user_id, user_pw)
    viewer.log("ROI 갱신됨") 
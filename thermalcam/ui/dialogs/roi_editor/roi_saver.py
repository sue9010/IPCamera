import requests
import time
from PyQt5.QtWidgets import QCheckBox, QMessageBox, QMainWindow
from thermalcam.ui.stream_handler import update_frame
from PyQt5.QtCore import QTimer
from thermalcam.core.roi import fetch_all_rois
from thermalcam.core.alarm import fetch_alarm_conditions
from thermalcam.ui.stream_handler import update_frame
from thermalcam.ui.roi_display_handler import init_roi_labels

class ROISaver:
    def __init__(self, ip, user_id, user_pw, roi_table, alarm_table, iso_table, parent=None):
        self.ip = ip
        self.user_id = user_id
        self.user_pw = user_pw
        self.roi_table = roi_table
        self.alarm_table = alarm_table
        self.iso_table = iso_table
        self.parent = parent  # QDialog 또는 QMainWindow
        
    def save_all(self):
        success = True
        MAX_RETRIES = 3

        # 🔍 변경 전 설정값 미리 가져오기
        original_rois = fetch_all_rois(self.ip, self.user_id, self.user_pw)
        if not original_rois:
            QMessageBox.warning(self.parent, "오류", "기존 ROI 데이터를 불러오지 못했습니다.")
            return

        for row in range(10):
            try:
                # 🔁 새 값 수집
                roi_chk = self.roi_table.cellWidget(row, 0)
                roi_checked = roi_chk.findChild(QCheckBox).isChecked() if roi_chk else False
                startx = int(self.roi_table.item(row, 1).text())
                starty = int(self.roi_table.item(row, 2).text())
                endx = int(self.roi_table.item(row, 3).text())
                endy = int(self.roi_table.item(row, 4).text())
                roi_use = "on" if roi_checked else "off"

                # 알람 값
                mode_box = self.alarm_table.cellWidget(row, 1)
                cond_box = self.alarm_table.cellWidget(row, 2)
                alarm_out_box = self.alarm_table.cellWidget(row, 6)
                temp_item = self.alarm_table.item(row, 3)
                start_item = self.alarm_table.item(row, 4)
                stop_item = self.alarm_table.item(row, 5)

                mode = mode_box.currentText() if mode_box else "maximum"
                condition = cond_box.currentText() if cond_box else "above"
                alarm_out = alarm_out_box.currentText() if alarm_out_box else "none"
                temperature = temp_item.text() if temp_item else ""
                start_delay = start_item.text() if start_item else ""
                stop_delay = stop_item.text() if stop_item else ""
                alarm_use = "on" if roi_checked else "off"

                # ISO 값
                iso_chk = self.iso_table.cellWidget(row, 0)
                iso_checked = iso_chk.findChild(QCheckBox).isChecked() if iso_chk else False
                iso_cond_box = self.iso_table.cellWidget(row, 1)
                iso_temp_item = self.iso_table.item(row, 2)
                iso_color_box = self.iso_table.cellWidget(row, 3)

                iso_condition = iso_cond_box.currentText() if iso_cond_box else "above"
                iso_temperature = iso_temp_item.text() if iso_temp_item else ""
                iso_color = iso_color_box.currentText() if iso_color_box else "red"
                iso_use = "on" if iso_checked else "off"

                # 🔍 기존 값과 비교
                prev = original_rois[row]
                changed = (
                    prev["used"] != (roi_use == "on") or
                    prev["coords"] != (startx, starty, endx, endy) or
                    prev["alarm"].get("alarm_use") != alarm_use or
                    prev["alarm"].get("mode") != mode or
                    prev["alarm"].get("condition") != condition or
                    prev["alarm"].get("temperature") != temperature or
                    prev["alarm"].get("start_delay") != start_delay or
                    prev["alarm"].get("stop_delay") != stop_delay or
                    prev["alarm"].get("alarm_out") != alarm_out or
                    prev["iso"].get("iso_use") != iso_use or
                    prev["iso"].get("condition") != iso_condition or
                    prev["iso"].get("temperature") != iso_temperature or
                    prev["iso"].get("color") != iso_color
                )

                if not changed:
                    continue  # 🚫 변경 없으면 skip

                # ✅ 변경된 경우에만 요청
                url = f"http://{self.ip}/cgi-bin/control/camthermalroi.cgi"
                params = {
                    "id": self.user_id,
                    "passwd": self.user_pw,
                    "action": f"setthermalroi{row}",
                    "roi_use": roi_use,
                    "startx": startx,
                    "starty": starty,
                    "endx": endx,
                    "endy": endy,
                    "alarm_use": alarm_use,
                    "mode": mode,
                    "condition": condition,
                    "temperature": temperature,
                    "start_delay": start_delay,
                    "stop_delay": stop_delay,
                    "alarm_out": alarm_out,
                    "iso_use": iso_use,
                    "iso_color": iso_color
                }

                if iso_use == "on":
                    params["condition"] = iso_condition
                    params["temperature"] = iso_temperature

                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        resp = requests.get(url, params=params, timeout=2)
                        if resp.status_code == 200 and "Error" not in resp.text:
                            break
                        else:
                            self.parent.log(f"[ROI {row}] 시도 {attempt} 실패: {resp.text}")
                    except requests.RequestException as e:
                        self.parent.log(f"[ROI {row}] 시도 {attempt} 예외 발생: {e}")
                    time.sleep(0.5)
                else:
                    self.parent.log(f"[ROI {row}] 모든 시도 실패")
                    success = False

            except Exception as e:
                self.parent.log(f"[ROI {row}] 저장 중 예외 발생: {e}")
                success = False

        # ✅ UI 갱신
        if success:
            if isinstance(self.parent, QMainWindow):
                self.parent.rois = fetch_all_rois(self.ip, self.user_id, self.user_pw)
                self.parent.roi_alarm_config = fetch_alarm_conditions(self.ip, self.user_id, self.user_pw)
                self.parent.should_draw_rois = True
                update_frame(self.parent)
                QTimer.singleShot(100, lambda: update_frame(self.parent))
            self.parent.log("ROI 설정 변경")
        else:
            QMessageBox.warning(self.parent, "저장 실패", "일부 ROI 설정 저장에 실패했습니다.")

from PyQt5.QtWidgets import QMessageBox
import requests



def fetch_alarm_conditions(ip, user_id, user_pw):
    alarm_list = []
    try:
        for i in range(10):  # ROI 0~9
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

            alarm_data = {
                "mode": data.get("mode", ""),
                "condition": data.get("condition", ""),
                "temperature": data.get("temperature", ""),
                "start_delay": data.get("start_delay", ""),
                "stop_delay": data.get("stop_delay", ""),
                "alarm_out": data.get("alarm_out", "")
            }

            alarm_list.append(alarm_data)
    except Exception as e:
        print(f"[fetch_alarm_conditions] 예외 발생: {e}")
        return None

    return alarm_list
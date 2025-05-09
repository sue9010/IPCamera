from roi_utils import fetch_all_rois

# fetch_alarm_conditions는 메인 뷰어에서 영상이 연결될 때 1번,
# 그리고 ROI가 갱신될 때마다 호출되어야 합니다.
def fetch_alarm_conditions(ip, user_id, user_pw):
    rois = fetch_all_rois(ip, user_id, user_pw)
    if rois is None:
        print("[오류] ROI 데이터를 가져올 수 없습니다. 로그인 정보를 확인하세요.")
        return []

    print("[설정된 알람 조건]")
    for idx, roi in enumerate(rois):
        alarm = roi.get("alarm", {})
        print(f"ROI{idx} - 사용: {alarm.get('alarm_use')}, 모드: {alarm.get('mode')}, 조건: {alarm.get('condition')}, ",
              f"온도: {alarm.get('temperature')}, 시작지연: {alarm.get('start_delay')}, 종료지연: {alarm.get('stop_delay')}")
    return rois

# evaluate_alarms는 열화상 TCP/IP 수신 시마다 호출되어야 합니다.
def evaluate_alarms(rois, thermal_data):
    for idx, roi in enumerate(rois):
        alarm = roi.get("alarm", {})
        use = alarm.get("alarm_use")
        condition = alarm.get("condition")
        threshold = alarm.get("temperature")

        if use != "on" or condition not in ("above", "below") or threshold is None:
            continue

        try:
            threshold = float(threshold)
            temp = thermal_data.get(idx, {}).get("max")
            if temp is None:
                continue
            temp = float(temp)

            if condition == "above" and temp > threshold:
                print(f"[알람] ROI{idx}: 온도 {temp}℃ > 기준 {threshold}℃")
            elif condition == "below" and temp < threshold:
                print(f"[알람] ROI{idx}: 온도 {temp}℃ < 기준 {threshold}℃")
        except Exception as e:
            print(f"[에러] ROI{idx} 알람 판별 중 오류: {e}")


if __name__ == "__main__":
    # 예시 테스트용
    ip = "192.168.0.56"
    user_id = "admin"
    user_pw = "admin"

    print("[알람 조건 로드 중...]")
    rois = fetch_alarm_conditions(ip, user_id, user_pw)

    print("\n[모의 온도 수신 데이터 평가 중...]")
    dummy_thermal_data = {
        0: {"max": 65.3},
        1: {"max": 72.0},
        2: {"max": 48.7},
    }

    evaluate_alarms(rois, dummy_thermal_data)

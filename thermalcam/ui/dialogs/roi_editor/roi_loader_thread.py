from PyQt5.QtCore import QThread
from thermalcam.core.roi import fetch_all_rois
from thermalcam.ui.dialogs.roi_editor.rtsp_utils import load_rtsp_frame

class ROILoaderThread(QThread):
    def __init__(self, ip, user_id, user_pw, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.user_id = user_id
        self.user_pw = user_pw

        self.frame = None
        self.resolution = (640, 480)
        self.roi_list = []

    def run(self):
        try:
            # RTSP 프레임 1장 캡처
            self.frame, self.resolution = load_rtsp_frame(self.ip, self)

            # ROI / 알람 / ISO 포함된 통합 데이터 로딩
            self.roi_list = fetch_all_rois(self.ip, self.user_id, self.user_pw) or [{} for _ in range(10)]

        except Exception as e:
            print(f"[ROILoaderThread] 로딩 실패: {e}")

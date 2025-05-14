import cv2
from PyQt5.QtWidgets import QMessageBox

def load_rtsp_frame(ip, parent=None):
    """
    RTSP 스트림에서 첫 프레임을 불러오고 (frame, resolution)을 반환.
    
    Args:
        ip (str): 카메라 IP 주소
        parent (QWidget): 오류 시 QMessageBox 표시용 부모
    
    Returns:
        tuple: (frame (numpy.ndarray), resolution (tuple: (width, height)))
    
    Raises:
        RuntimeError: 프레임 수신 실패 시 예외 발생
    """
    try:
        rtsp_url = f"rtsp://{ip}:554/stream1"
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            raise RuntimeError("RTSP 프레임 캡처 실패")

        resolution = (frame.shape[1], frame.shape[0])  # (width, height)
        return frame, resolution

    except Exception as e:
        if parent:
            QMessageBox.critical(parent, "RTSP 오류", f"프레임 캡처 실패:\n{str(e)}")
        raise

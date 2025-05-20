import os
import sys
import cv2

def resource_path(relative_path):
    try:
        # PyInstaller 실행 환경
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class SuperResolution:
    def __init__(self, model_name='EDSR_x2.pb'):  # ← x4 → x2 로 변경
        self.model_path = resource_path(os.path.join("thermalcam", "resources", "models", model_name))
        print("[SR] 모델 경로:", self.model_path)
        assert os.path.exists(self.model_path), "❌ 모델 파일이 존재하지 않음!"
        self.sr = cv2.dnn_superres.DnnSuperResImpl_create()
        self.sr.readModel(self.model_path)
        self.sr.setModel("edsr", 2)  # ← 여기도 2배로 설정

    def upscale(self, image):
        """
        :param image: numpy.ndarray (BGR image)
        :return: upscaled image
        """
        return self.sr.upsample(image)

    def upscale_and_save(self, image, save_path):
        """
        :param image: numpy.ndarray (BGR image)
        :param save_path: 저장할 PNG 파일 경로 (예: 'output.png')
        """
        upscaled = self.upscale(image)
        # PNG로 저장
        cv2.imwrite(save_path, upscaled)
        print(f"[SR] 업스케일 이미지 저장 완료: {save_path}")

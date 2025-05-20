from thermalcam.core.super_resolution import SuperResolution
import cv2

sr = SuperResolution()
img = cv2.imread("test.png")

# 업스케일 및 저장
sr.upscale_and_save(img, "upscaled_result.png")

# 저장된 이미지 불러와서 확인
upscaled = cv2.imread("upscaled_result.png")

print(f"원본 해상도: {img.shape}")
print(f"업스케일 해상도: {upscaled.shape}")
cv2.imshow("Super Res", upscaled)
cv2.waitKey(0)

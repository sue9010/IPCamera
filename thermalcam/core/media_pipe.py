import mediapipe as mp
import cv2

class MediaPipePoseDetector:
    def __init__(self):
        self.pose = mp.solutions.pose.Pose()
        self.drawer = mp.solutions.drawing_utils
        self.connections = mp.solutions.pose.POSE_CONNECTIONS

    def detect_and_draw(self, frame):
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.pose.process(image_rgb)
        if result.pose_landmarks:
            self.drawer.draw_landmarks(frame, result.pose_landmarks, self.connections)
        return frame

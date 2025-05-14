# thermalcam/core/frame_reader.py

from threading import Thread
from collections import deque
import cv2
import time

class FrameReader(Thread):
    def __init__(self, url, delay_sec):
        super().__init__(daemon=True)
        self.url = url
        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.delay_frames = int(delay_sec * fps)
        self.frames = deque(maxlen=self.delay_frames + 1)
        self.running = True

    def run(self):
        while self.running:
            if not self.cap.isOpened():
                break
            ret, frame = self.cap.read()
            if not self.running:
                break
            if ret:
                self.frames.append(frame)
            else:
                time.sleep(0.01)

        if self.cap.isOpened():
            self.cap.release()

    def get_delayed(self):
        if not self.running or not self.cap.isOpened():
            return None
        if len(self.frames) == self.frames.maxlen:
            return self.frames[0]
        return None

    def stop(self):
        self.running = False

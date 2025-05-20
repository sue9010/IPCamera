import mediapipe as mp
import cv2
import time

class MediaPipePoseDetector:
    def __init__(self, main_window=None):
        self.pose = mp.solutions.pose.Pose()
        self.drawer = mp.solutions.drawing_utils
        self.connections = mp.solutions.pose.POSE_CONNECTIONS
        self.main_window = main_window

        # 포즈 지속 시간 추적용 상태 변수
        self.pose_start_time = {
            "both_arms_up": None,
            "one_arm_up": None,
            "t_pose": None
        }
        self.pose_logged = {
            "both_arms_up": False,
            "one_arm_up": False,
            "t_pose": False
        }

    def log(self, message):
        if self.main_window and hasattr(self.main_window, "log"):
            self.main_window.log(message)
        else:
            print(message)

    def _check_pose_hold(self, pose_key, is_active):
        now = time.time()
        if is_active:
            if self.pose_start_time[pose_key] is None:
                self.pose_start_time[pose_key] = now
                self.pose_logged[pose_key] = False
            elif not self.pose_logged[pose_key] and now - self.pose_start_time[pose_key] >= 1:
                self.pose_logged[pose_key] = True
                return True
        else:
            self.pose_start_time[pose_key] = None
            self.pose_logged[pose_key] = False
        return False

    def detect_and_draw(self, frame):
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.pose.process(image_rgb)

        if result.pose_landmarks:
            self.drawer.draw_landmarks(frame, result.pose_landmarks, self.connections)

            landmarks = result.pose_landmarks.landmark
            lw, rw, ls, rs = landmarks[15], landmarks[16], landmarks[11], landmarks[12]

            if all(pt.visibility > 0.5 for pt in [lw, rw, ls, rs]):
                # 🔹 개선된 기준
                left_arm_up = lw.y < ls.y - 0.1   # Y 차이 더 명확히
                right_arm_up = rw.y < rs.y - 0.1

                y_close = abs(lw.y - ls.y) < 0.1 and abs(rw.y - rs.y) < 0.1
                x_outward = lw.x < ls.x - 0.1 and rw.x > rs.x + 0.1

                # ✈️ T자 자세를 먼저 평가
                if self._check_pose_hold("t_pose", y_close and x_outward):
                    self.log("[포즈] ✈️ 팔을 양 옆으로 펼친 자세 (T자 자세) 감지됨")

                # 🙌 양 팔을 든 자세 (T-포즈가 아닌 경우에만)
                elif self._check_pose_hold("both_arms_up", left_arm_up and right_arm_up and not (y_close and x_outward)):
                    self.log("[포즈] 🙌 양 팔을 든 자세 감지됨")

                # 🙋 한 팔만 든 자세
                elif self._check_pose_hold("one_arm_up", (left_arm_up or right_arm_up) and not (left_arm_up and right_arm_up)):
                    self.log("[포즈] 🙋 한 팔만 든 자세 감지됨")

        return frame

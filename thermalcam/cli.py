import sys
from PyQt5.QtWidgets import QApplication
from thermalcam.ui.main_window import OpenCVViewer

def main():
    app = QApplication(sys.argv)
    viewer = OpenCVViewer()
    viewer.show()  # ✅ 반드시 있어야 함
    sys.exit(app.exec_())  # ✅ 앱이 유지되려면 필수

if __name__ == "__main__":
    try:
        import sys
        from PyQt5.QtWidgets import QApplication
        from thermalcam.ui.main_window import OpenCVViewer

        print("[CLI] QApplication 시작")
        app = QApplication(sys.argv)
        print("[CLI] OpenCVViewer 생성")
        viewer = OpenCVViewer()
        print("[CLI] viewer.show() 호출")
        viewer.show()
        print("[CLI] 이벤트 루프 진입")
        sys.exit(app.exec_())

    except Exception as e:
        with open("error_log.txt", "w", encoding="utf-8") as f:
            import traceback
            f.write(traceback.format_exc())

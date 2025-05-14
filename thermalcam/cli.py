import sys
from PyQt5.QtWidgets import QApplication
from thermalcam.ui.main_window import OpenCVViewer

def main():
    app = QApplication(sys.argv)
    viewer = OpenCVViewer()
    viewer.show()  # ✅ 반드시 있어야 함
    sys.exit(app.exec_())  # ✅ 앱이 유지되려면 필수

if __name__ == "__main__":
    main()
# main.py
import sys
from PyQt5.QtWidgets import QApplication
from opencv_viewer_module import OpenCVViewer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = OpenCVViewer()
    viewer.show()
    sys.exit(app.exec_())

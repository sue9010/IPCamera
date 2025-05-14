from PyQt5.QtWidgets import QRadioButton

class ROICaptureHandler:
    def __init__(self, roi_table, drawer):
        """
        roi_table: ROI 설정이 들어 있는 QTableWidget
        drawer: ROIDrawer 인스턴스 (draw_rois_on_image 메서드 포함)
        """
        self.roi_table = roi_table
        self.drawer = drawer  # ROIDrawer 인스턴스

    def handle_roi_drawn(self, x1, y1, x2, y2):
        """
        캡처 이미지에서 ROI 사각형이 새로 그려졌을 때 호출됨.
        선택된 라디오 버튼을 기준으로 테이블 값을 갱신함.
        """
        for row in range(10):
            radio_widget = self.roi_table.cellWidget(row, 5)
            if not radio_widget:
                continue

            radio = radio_widget.findChild(QRadioButton)
            if radio and radio.isChecked():
                self.roi_table.item(row, 1).setText(str(x1))
                self.roi_table.item(row, 2).setText(str(y1))
                self.roi_table.item(row, 3).setText(str(x2))
                self.roi_table.item(row, 4).setText(str(y2))
                break

        self.drawer.draw_rois_on_image()

from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtCore import Qt

class ROISyncManager:
    def __init__(self, roi_table, alarm_table, iso_table, drawer=None):
        """
        drawer: ROIDrawer 인스턴스 (있을 경우 draw_rois_on_image 호출)
        """
        self.roi_table = roi_table
        self.alarm_table = alarm_table
        self.iso_table = iso_table
        self.drawer = drawer

    def sync_is_used(self, row, state):
        """특정 row의 is_used 상태를 ROI/알람/ISO 테이블 전체에 동기화"""
        tables = [self.roi_table, self.alarm_table, self.iso_table]
        for table in tables:
            try:
                if not table:
                    continue
                widget = table.cellWidget(row, 0)
                if not widget: 
                    continue
                chk = widget.findChild(QCheckBox)
                if chk and chk.isChecked() != (state == Qt.Checked):
                    chk.blockSignals(True)
                    chk.setChecked(state == Qt.Checked)
                    chk.blockSignals(False)
            except Exception as e:
                print(f"[is_used 동기화 오류] {table.objectName()} row {row}: {e}")

        if self.drawer:
            self.drawer.draw_rois_on_image()

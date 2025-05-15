from PyQt5.QtWidgets import (
    QDialog, QTableWidget, QPushButton, QCheckBox, QRadioButton, QLabel
)
from PyQt5 import uic
from importlib.resources import path

from PyQt5.QtGui import QMovie
from PyQt5.QtCore import Qt, pyqtSlot

from thermalcam.ui.widgets.roi_capture_widget import ROICaptureLabel
from .roi_loader import ROILoader
from .roi_drawer import ROIDrawer
from .roi_saver import ROISaver
from .roi_sync import ROISyncManager
from .roi_capture_handler import ROICaptureHandler
from .roi_loader_thread import ROILoaderThread

import os

class SetROIPopup(QDialog):
    def __init__(self, ip, user_id, user_pw, main_window, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.user_id = user_id
        self.user_pw = user_pw
        self.main_window = main_window
        self.frame_original = None
        self.resolution = (640, 480)

        with path("thermalcam.resources.ui", "roi.ui") as ui_file:
            uic.loadUi(str(ui_file), self)

        self.tabWidget.setCurrentIndex(0)

        # 위젯 찾기
        self.capture_image = self.findChild(ROICaptureLabel, "capture_image")
        self.iso_table = self.findChild(QTableWidget, "iso_table")
        self.alarm_table = self.findChild(QTableWidget, "alarm_table")
        self.roi_table = self.findChild(QTableWidget, "roi_table")
        self.save_button = self.findChild(QPushButton, "btn_save")

        # 컴포넌트 조립
        self.drawer = ROIDrawer(self.roi_table, self.capture_image)
        self.loader = ROILoader(self.ip, self.user_id, self.user_pw, self.roi_table, self.alarm_table, self.iso_table)
        self.saver = ROISaver(
            self.ip, self.user_id, self.user_pw,
            self.roi_table, self.alarm_table, self.iso_table,
            parent=self.main_window
        )
        self.sync = ROISyncManager(self.roi_table, self.alarm_table, self.iso_table, self.drawer)
        self.capture_handler = ROICaptureHandler(self.roi_table, self.drawer)

        self.capture_image.on_roi_drawn = self.capture_handler.handle_roi_drawn
        if self.save_button:
            self.save_button.clicked.connect(self.saver.save_all)

        # ROI 동기화 및 핸들링 연결
        self._connect_usage_sync_signals()
        self.capture_image.on_roi_selected = self._on_roi_selected_from_image
        self.capture_image.on_roi_moved = self._on_roi_moved_from_image
        self.roi_table.cellChanged.connect(self._on_roi_table_cell_changed)
        self.alarm_table.itemChanged.connect(self._sync_alarm_to_iso)
        self.iso_table.itemChanged.connect(self._sync_iso_to_alarm)

        # ✅ 로딩 스피너 오버레이
        gif_path = os.path.join(os.path.dirname(__file__), "../../../resources/icons/spinner.gif")
        gif_path = os.path.normpath(gif_path)

        self.spinner = QLabel(self.capture_image)
        self.spinner.setStyleSheet("background-color: rgba(0, 0, 0, 80); border-radius: 20px;")
        self.spinner.setAlignment(Qt.AlignCenter)
        self.spinner.setFixedSize(480, 480)  # 🔹 크기 변경
        self.spinner.setScaledContents(True)  # 이미지 크기에 맞게 채움
        self.spinner.setText("")  # 텍스트 제거

        self.spinner_movie = QMovie(gif_path)
        self.spinner.setMovie(self.spinner_movie)
        self.spinner_movie.start()
        self.spinner.show()

        # ✅ 스레드 로더 시작
        self.loader_thread = ROILoaderThread(self.ip, self.user_id, self.user_pw)
        self.loader_thread.finished.connect(self.on_loader_finished)
        self.loader_thread.start()

    @pyqtSlot()
    def on_loader_finished(self):
        self.frame_original = self.loader_thread.frame
        self.resolution = self.loader_thread.resolution

        self.drawer.set_frame(self.frame_original)
        self.capture_image.image_width = self.resolution[0]
        self.capture_image.image_height = self.resolution[1]

        self.loader.roi_data = self.loader_thread.roi_list
        self.loader.load_all()
        self.drawer.draw_rois_on_image()

        # ✅ 로딩 스피너 숨김
        self.spinner.hide()
        self.spinner_movie.stop()

        self.main_window.log("[로딩 완료] ROI 프레임 및 테이블 반영됨")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "spinner"):
            cx = self.capture_image.width() // 2 - self.spinner.width() // 2
            cy = self.capture_image.height() // 2 - self.spinner.height() // 2
            self.spinner.move(cx, cy)


    def _on_roi_selected_from_image(self, row):
        radio_widget = self.roi_table.cellWidget(row, 5)
        if radio_widget:
            radio = radio_widget.findChild(QRadioButton)
            if radio and not radio.isChecked():
                radio.setChecked(True)

    def _on_roi_moved_from_image(self, row, dx, dy):
        try:
            for col, offset in zip((1, 2, 3, 4), (dx, dy, dx, dy)):
                item = self.roi_table.item(row, col)
                if item:
                    val = int(item.text()) + offset
                    item.setText(str(val))
            self.drawer.draw_rois_on_image()
        except Exception as e:
            self.main_window.log(f"[ROI 이동 오류] row {row}, dx={dx}, dy={dy}: {e}")

    def _connect_usage_sync_signals(self):
        for table in [self.roi_table, self.alarm_table, self.iso_table]:
            if not table:
                continue
            for row in range(10):
                widget = table.cellWidget(row, 0)
                if not widget:
                    continue
                chk = widget.findChild(QCheckBox)
                if chk:
                    chk.stateChanged.connect(lambda state, r=row: self.sync.sync_is_used(r, state))

    def _on_roi_table_cell_changed(self, row, col):
        if col in (1, 2, 3, 4):
            self.drawer.draw_rois_on_image()

    def _sync_alarm_to_iso(self, item):
        row = item.row()
        col = item.column()
        if col == 3:
            try:
                value = item.text()
                target = self.iso_table.item(row, 2)
                if target and target.text() != value:
                    self.iso_table.blockSignals(True)
                    target.setText(value)
                    self.iso_table.blockSignals(False)
            except Exception as e:
                self.main_window.log(f"[알람→ISO 동기화 오류] row={row}: {e}")

    def _sync_iso_to_alarm(self, item):
        row = item.row()
        col = item.column()
        if col == 2:
            try:
                value = item.text()
                target = self.alarm_table.item(row, 3)
                if target and target.text() != value:
                    self.alarm_table.blockSignals(True)
                    target.setText(value)
                    self.alarm_table.blockSignals(False)
            except Exception as e:
                self.main_window.log(f"[ISO→알람 동기화 오류] row={row}: {e}")

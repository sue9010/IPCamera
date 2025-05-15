from PyQt5.QtWidgets import QDialog, QTableWidget, QPushButton, QCheckBox, QRadioButton
from PyQt5 import uic
from importlib.resources import path

from thermalcam.ui.widgets.roi_capture_widget import ROICaptureLabel
from .roi_loader import ROILoader
from .roi_drawer import ROIDrawer
from .roi_saver import ROISaver
from .roi_sync import ROISyncManager
from .roi_capture_handler import ROICaptureHandler
from .roi_loader_thread import ROILoaderThread
from PyQt5.QtCore import pyqtSlot


 
class SetROIPopup(QDialog):
    def __init__(self, ip, user_id, user_pw, main_window, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.user_id = user_id
        self.user_pw = user_pw
        self.main_window = main_window
        self.frame_original = None  # 아직 없음
        self.resolution = (640, 480)  # 기본값

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

        # ✅ 기본 상태로 초기 설정 (아직 프레임 없음)
        # self.drawer.set_frame(None)

        # ROI 동기화 및 핸들링 연결
        self._connect_usage_sync_signals()
        self.capture_image.on_roi_selected = self._on_roi_selected_from_image
        self.capture_image.on_roi_moved = self._on_roi_moved_from_image
        self.roi_table.cellChanged.connect(self._on_roi_table_cell_changed)
        self.alarm_table.itemChanged.connect(self._sync_alarm_to_iso)
        self.iso_table.itemChanged.connect(self._sync_iso_to_alarm)

        # ROI 로딩 스레드 시작
        self.loader_thread = ROILoaderThread(self.ip, self.user_id, self.user_pw)
        self.loader_thread.finished.connect(self.on_loader_finished)
        self.loader_thread.start()


    def _on_roi_selected_from_image(self, row):
        """이미지에서 ROI 클릭 시 테이블의 라디오 버튼 체크"""
        radio_widget = self.roi_table.cellWidget(row, 5)
        if radio_widget:
            radio = radio_widget.findChild(QRadioButton)
            if radio and not radio.isChecked():
                radio.setChecked(True)

    def _on_roi_moved_from_image(self, row, dx, dy):
        """ROI가 이미지에서 드래그로 이동됐을 때 테이블 좌표를 업데이트"""
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
        """roi/alarm/iso 테이블의 is_used 체크박스에 stateChanged 시그널 연결"""
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
        """ROI 좌표 셀 수정 시 이미지 업데이트"""
        if col in (1, 2, 3, 4):  # StartX, StartY, EndX, EndY
            self.drawer.draw_rois_on_image()

    def _sync_alarm_to_iso(self, item):
        """알람 탭에서 온도 수정 → ISO 탭으로 반영"""
        row = item.row()
        col = item.column()
        if col == 3:  # temperature 열
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
        """ISO 탭에서 온도 수정 → 알람 탭으로 반영"""
        row = item.row()
        col = item.column()
        if col == 2:  # temperature 열
            try:
                value = item.text()
                target = self.alarm_table.item(row, 3)
                if target and target.text() != value:
                    self.alarm_table.blockSignals(True)
                    target.setText(value)
                    self.alarm_table.blockSignals(False)
            except Exception as e:
                self.main_window.log(f"[ISO→알람 동기화 오류] row={row}: {e}")

    @pyqtSlot()
    def on_loader_finished(self):
        # RTSP 프레임 적용
        self.frame_original = self.loader_thread.frame
        self.resolution = self.loader_thread.resolution
        self.drawer.set_frame(self.frame_original)
        self.capture_image.image_width = self.resolution[0]
        self.capture_image.image_height = self.resolution[1]

        # ROI 데이터를 로컬에 복사 (setattr 방식)
        self.loader.roi_data = self.loader_thread.roi_list
        self.loader.load_all()  # roi_data 있는 경우 이걸로 그림

        self.drawer.draw_rois_on_image()
        self.main_window.log("[로딩 완료] ROI + RTSP 프레임 반영됨")

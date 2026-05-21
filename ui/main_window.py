"""OfficeMonitor 메인 윈도우 — 전체 통합"""

import os
import time
import cv2
import numpy as np
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStatusBar, QComboBox, QStackedWidget,
    QSizePolicy, QFileDialog, QSystemTrayIcon, QMenu,
)
from PyQt6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QIcon, QShortcut, QKeySequence, QPixmap

from .camera_widget import CameraWidget
from .styles import MAIN_STYLE
from .header_bar import HeaderBar
from .kpi_card import KPICard
from .visitor_timeline import VisitorTimeline
from .design_tokens import Q_CYAN, Q_GREEN, Q_RED, Q_AMBER
from .toast_widget import ToastWidget

import database


DATA_DIR = r"C:\OfficeMonitor"
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class MainWindow(QMainWindow):
    """메인 윈도우"""

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self._camera_thread = None
        self._detection_thread = None
        self._recording_thread = None
        self._last_frame = None
        self._frame_count = 0
        self._fps_display = 0.0
        self._panel_expanded = True
        self._panel_width = 260
        self._top_panel_expanded = True

        self.setWindowTitle("OfficeMonitor")
        self.setMinimumSize(400, 300)
        self.resize(1200, 750)
        self.setStyleSheet(MAIN_STYLE)

        database.init_db()

        self._setup_ui()
        self._setup_statusbar()
        self._setup_shortcuts()
        self._setup_tray()
        self._start_engines()

        # FPS 갱신 타이머
        self._fps_timer = QTimer(self)
        self._fps_timer.timeout.connect(self._update_fps)
        self._fps_timer.start(1000)

        # KPI 갱신 타이머
        self._kpi_timer = QTimer(self)
        self._kpi_timer.timeout.connect(self._update_kpi)
        self._kpi_timer.start(5000)
        self._update_kpi()

    # ═══════════════════════════════════════
    # UI 구성
    # ═══════════════════════════════════════

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 헤더바 (top_panel에 포함, 토글로 같이 접힘) ──
        self.header = HeaderBar()
        self.header.tab_changed.connect(self._on_tab_changed)
        self._header_ref = self.header  # top_panel 조립 시 사용
        main_layout.addWidget(self.header)

        # ── 탭 콘텐츠 (QStackedWidget) ──
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_monitoring_view())
        self.stack.addWidget(self._create_visitor_view())
        self.stack.addWidget(self._create_stats_view())
        main_layout.addWidget(self.stack, 1)

    def _create_monitoring_view(self) -> QWidget:
        """탭 1: 모니터링 뷰"""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(12, 8, 12, 8)
        page_layout.setSpacing(8)

        # ── 상단 패널 (KPI + 툴바) ──
        self.top_panel = QWidget()
        top_panel_layout = QVBoxLayout(self.top_panel)
        top_panel_layout.setContentsMargins(0, 0, 0, 0)
        top_panel_layout.setSpacing(8)

        # KPI 카드 행
        kpi_widget = QWidget()
        kpi_row = QHBoxLayout(kpi_widget)
        kpi_row.setContentsMargins(0, 0, 0, 0)
        kpi_row.setSpacing(12)

        self.kpi_visitors = KPICard("오늘 방문자", "0", Q_CYAN)
        self.kpi_faces = KPICard("감지 중", "0", Q_GREEN)
        self.kpi_rec_time = KPICard("녹화 시간", "00:00", Q_RED)
        self.kpi_storage = KPICard("저장 용량", "0 MB", Q_AMBER)

        kpi_row.addWidget(self.kpi_visitors)
        kpi_row.addWidget(self.kpi_faces)
        kpi_row.addWidget(self.kpi_rec_time)
        kpi_row.addWidget(self.kpi_storage)
        top_panel_layout.addWidget(kpi_widget)

        # 툴바
        toolbar = QWidget()
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(4, 4, 4, 4)
        tb_layout.setSpacing(12)

        cam_label = QLabel("카메라")
        cam_label.setObjectName("subtitleLabel")
        self.combo_camera = QComboBox()
        self.combo_camera.addItem("Camera 0")
        self.combo_camera.addItem("Camera 1")
        self.combo_camera.currentIndexChanged.connect(self._on_camera_changed)

        self.btn_record = QPushButton("● 녹화")
        self.btn_record.setObjectName("btnRecord")
        self.btn_record.setFixedWidth(100)
        self.btn_record.clicked.connect(self._toggle_recording)

        self.btn_pause = QPushButton("⏸ 일시정지")
        self.btn_pause.setFixedWidth(110)
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._toggle_pause)

        self.btn_capture = QPushButton("📷 캡처")
        self.btn_capture.setObjectName("btnCapture")
        self.btn_capture.setFixedWidth(100)
        self.btn_capture.clicked.connect(self._capture_snapshot)

        self.btn_register = QPushButton("👤 얼굴등록")
        self.btn_register.setObjectName("btnCapture")
        self.btn_register.setFixedWidth(110)
        self.btn_register.clicked.connect(self._register_face_from_frame)

        tb_layout.addWidget(cam_label)
        tb_layout.addWidget(self.combo_camera)
        tb_layout.addSpacing(12)
        tb_layout.addWidget(self.btn_record)
        tb_layout.addWidget(self.btn_pause)
        tb_layout.addSpacing(12)
        tb_layout.addWidget(self.btn_capture)
        tb_layout.addWidget(self.btn_register)
        tb_layout.addStretch()
        top_panel_layout.addWidget(toolbar)

        page_layout.addWidget(self.top_panel)

        # 상단 토글 버튼 (가로 바)
        self.btn_toggle_top = QPushButton("▲")
        self.btn_toggle_top.setObjectName("topPanelToggle")
        self.btn_toggle_top.setFixedHeight(16)
        self.btn_toggle_top.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_top.clicked.connect(self._toggle_top_panel)
        page_layout.addWidget(self.btn_toggle_top)

        # ── 메인 콘텐츠 (카메라 + 슬라이드 패널) ──
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.camera_widget = CameraWidget()
        content_layout.addWidget(self.camera_widget, 1)

        self.btn_toggle_panel = QPushButton("◀")
        self.btn_toggle_panel.setObjectName("panelToggle")
        self.btn_toggle_panel.setFixedWidth(20)
        self.btn_toggle_panel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_panel.clicked.connect(self._toggle_right_panel)
        content_layout.addWidget(self.btn_toggle_panel)

        self.right_panel = self._create_right_panel()
        self.right_panel.setFixedWidth(self._panel_width)
        content_layout.addWidget(self.right_panel)

        page_layout.addWidget(content_area, 1)
        return page

    def _create_collapsible_card(self, title_text: str) -> tuple:
        card = QFrame()
        card.setObjectName("glassCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        header = QPushButton(f"  ▼  {title_text}")
        header.setObjectName("cardHeader")
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        card_layout.addWidget(header)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 4, 16, 12)
        content_layout.setSpacing(8)
        card_layout.addWidget(content)

        def toggle():
            if content.isVisible():
                content.setVisible(False)
                header.setText(f"  ▶  {title_text}")
            else:
                content.setVisible(True)
                header.setText(f"  ▼  {title_text}")
        header.clicked.connect(toggle)
        return card, content_layout

    def _create_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(0)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(8)

        # 카메라 정보
        cam_card, cam_lay = self._create_collapsible_card("카메라 정보")
        self.lbl_cam_status = QLabel("연결 대기 중...")
        self.lbl_cam_status.setObjectName("statusError")
        cam_lay.addWidget(self.lbl_cam_status)
        self.lbl_cam_resolution = QLabel("해상도: -")
        self.lbl_cam_resolution.setObjectName("subtitleLabel")
        cam_lay.addWidget(self.lbl_cam_resolution)
        self.lbl_cam_fps = QLabel("FPS: -")
        self.lbl_cam_fps.setObjectName("subtitleLabel")
        cam_lay.addWidget(self.lbl_cam_fps)
        layout.addWidget(cam_card)

        # 감지 상태
        det_card, det_lay = self._create_collapsible_card("감지 상태")
        self.lbl_face_count = QLabel("감지된 얼굴: 0")
        self.lbl_face_count.setObjectName("subtitleLabel")
        det_lay.addWidget(self.lbl_face_count)
        self.lbl_today_visitors = QLabel("오늘 방문자: 0")
        self.lbl_today_visitors.setObjectName("subtitleLabel")
        det_lay.addWidget(self.lbl_today_visitors)
        layout.addWidget(det_card)

        # 녹화 상태
        rec_card, rec_lay = self._create_collapsible_card("녹화 상태")
        self.lbl_rec_status = QLabel("대기 중")
        self.lbl_rec_status.setObjectName("subtitleLabel")
        rec_lay.addWidget(self.lbl_rec_status)
        self.lbl_rec_time = QLabel("녹화 시간: 00:00:00")
        self.lbl_rec_time.setObjectName("subtitleLabel")
        rec_lay.addWidget(self.lbl_rec_time)
        layout.addWidget(rec_card)

        # 방문자 타임라인
        self.timeline = VisitorTimeline()
        layout.addWidget(self.timeline, 1)

        return panel

    def _create_visitor_view(self) -> QWidget:
        """탭 2: 방문자 관리 (Phase 4에서 완성)"""
        from .visitor_manager import VisitorManagerView
        self._visitor_view = VisitorManagerView(self)
        return self._visitor_view

    def _create_stats_view(self) -> QWidget:
        """탭 3: 통계 (Phase 4에서 완성)"""
        from .stats_view import StatsView
        self._stats_view = StatsView(self)
        return self._stats_view

    # ═══════════════════════════════════════
    # 엔진 시작
    # ═══════════════════════════════════════

    def _start_engines(self):
        from monitor_engine import CameraThread
        from detection_engine import DetectionThread
        from recording_engine import RecordingThread

        cam_cfg = self.config.get("camera", {})

        # 카메라 스레드
        self._camera_thread = CameraThread(
            camera_id=cam_cfg.get("id", 0),
            resolution=tuple(cam_cfg.get("resolution", [1280, 720])),
            fallback_ids=cam_cfg.get("fallback_ids", []),
        )
        self._camera_thread.frame_ready.connect(self._on_frame)
        self._camera_thread.camera_status.connect(self._on_camera_status)
        self._camera_thread.camera_info.connect(self._on_camera_info)
        self._camera_thread.start()

        # 감지 스레드
        self._detection_thread = DetectionThread(self.config)
        self._detection_thread.faces_detected.connect(self._on_faces_detected)
        self._detection_thread.visit_logged.connect(self._on_visit_logged)
        self._detection_thread.start()

        # 녹화 스레드
        self._recording_thread = RecordingThread(self.config)
        self._recording_thread.status_changed.connect(self._on_rec_status)
        self._recording_thread.time_updated.connect(self._on_rec_time)
        self._recording_thread.start()

        # 자동 녹화
        if self.config.get("recording", {}).get("auto_start", False):
            QTimer.singleShot(2000, self._toggle_recording)

    # ═══════════════════════════════════════
    # 프레임 처리
    # ═══════════════════════════════════════

    def _on_frame(self, frame: np.ndarray, timestamp: float):
        self._last_frame = frame
        self._frame_count += 1
        self.camera_widget.update_frame(frame)

        # 감지/녹화 스레드에 프레임 전달
        if self._detection_thread:
            self._detection_thread.set_frame(frame)
        if self._recording_thread:
            self._recording_thread.set_frame(frame)

    def _on_faces_detected(self, faces: list):
        self.camera_widget.update_frame(self._last_frame, faces)
        self.lbl_face_count.setText(f"감지된 얼굴: {len(faces)}")
        self.kpi_faces.set_value(str(len(faces)))

    def _on_visit_logged(self, name: str, is_registered: bool):
        now = datetime.now().strftime("%H:%M")
        self.timeline.add_visitor(now, name, is_registered=is_registered)
        self._update_kpi()

        # 토스트 알림
        msg = f"{'등록됨' if is_registered else '미등록'}: {name}"
        ToastWidget.show_toast(self, msg, is_registered)

        # 미등록 방문자 경고음
        if not is_registered:
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass

    # ═══════════════════════════════════════
    # 캡처 / 녹화
    # ═══════════════════════════════════════

    def _capture_snapshot(self):
        if self._last_frame is None:
            return
        ts = time.strftime("%Y%m%d_%H%M%S")
        snap_dir = os.path.join(DATA_DIR, "snapshots")
        os.makedirs(snap_dir, exist_ok=True)
        path = os.path.join(snap_dir, f"snap_{ts}.png")
        cv2.imwrite(path, self._last_frame)
        database.add_snapshot(path)
        self.status_bar.showMessage(f"캡처 저장: {path}")
        ToastWidget.show_toast(self, f"캡처 저장됨", True)

    def _toggle_recording(self):
        if not self._recording_thread:
            return
        if self._recording_thread.is_recording:
            self._recording_thread.stop_recording()
            self.btn_record.setText("● 녹화")
            self.btn_record.setProperty("recording", "false")
            self.btn_pause.setEnabled(False)
        else:
            self._recording_thread.start_recording()
            self.btn_record.setText("■ 중지")
            self.btn_record.setProperty("recording", "true")
            self.btn_pause.setEnabled(True)
        self.btn_record.style().unpolish(self.btn_record)
        self.btn_record.style().polish(self.btn_record)

    def _toggle_pause(self):
        if not self._recording_thread:
            return
        self._recording_thread.pause_recording()

    def _on_rec_status(self, status: str):
        labels = {"recording": "녹화 중", "paused": "일시정지", "stopped": "대기 중"}
        self.lbl_rec_status.setText(labels.get(status, status))
        if status == "paused":
            self.btn_pause.setText("▶ 재개")
        else:
            self.btn_pause.setText("⏸ 일시정지")

    def _on_rec_time(self, time_str: str):
        self.lbl_rec_time.setText(f"녹화 시간: {time_str}")
        self.kpi_rec_time.set_value(time_str[:5])

    # ═══════════════════════════════════════
    # 얼굴 등록
    # ═══════════════════════════════════════

    def _register_face_from_frame(self):
        """현재 감지된 얼굴 중 첫 번째를 등록"""
        if self._last_frame is None or not self._detection_thread:
            self.status_bar.showMessage("카메라 프레임이 없습니다")
            return

        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "얼굴 등록", "이름을 입력하세요:")
        if not ok or not name.strip():
            return

        # 현재 프레임에서 얼굴 감지
        try:
            faces = self._detection_thread._app.get(self._last_frame)
            if not faces:
                self.status_bar.showMessage("얼굴이 감지되지 않았습니다")
                return
            face = faces[0]
            self._detection_thread.register_face(name.strip(), face.embedding)
            self.status_bar.showMessage(f"'{name.strip()}' 등록 완료")
            ToastWidget.show_toast(self, f"'{name.strip()}' 등록됨", True)
        except Exception as e:
            self.status_bar.showMessage(f"등록 실패: {e}")

    # ═══════════════════════════════════════
    # 카메라 상태
    # ═══════════════════════════════════════

    def _on_camera_status(self, message: str, is_ok: bool):
        self.lbl_cam_status.setText(message)
        self.lbl_cam_status.setObjectName("statusOK" if is_ok else "statusError")
        self.lbl_cam_status.setStyleSheet("")
        self.lbl_cam_status.style().unpolish(self.lbl_cam_status)
        self.lbl_cam_status.style().polish(self.lbl_cam_status)
        if not is_ok:
            self.camera_widget.set_status(message, False)
        self.status_bar.showMessage(message)

    def _on_camera_info(self, info: dict):
        self.lbl_cam_resolution.setText(f"해상도: {info['width']}x{info['height']}")

    def _on_camera_changed(self, index: int):
        if self._camera_thread and self._camera_thread.isRunning():
            self._camera_thread.stop()
        from monitor_engine import CameraThread
        cam_cfg = self.config.get("camera", {})
        self._camera_thread = CameraThread(
            camera_id=index,
            resolution=tuple(cam_cfg.get("resolution", [1280, 720])),
        )
        self._camera_thread.frame_ready.connect(self._on_frame)
        self._camera_thread.camera_status.connect(self._on_camera_status)
        self._camera_thread.camera_info.connect(self._on_camera_info)
        self._camera_thread.start()

    # ═══════════════════════════════════════
    # KPI / FPS 갱신
    # ═══════════════════════════════════════

    def _update_fps(self):
        self._fps_display = self._frame_count
        self._frame_count = 0
        self.lbl_cam_fps.setText(f"FPS: {self._fps_display}")

    def _update_kpi(self):
        visits = database.get_today_visits()
        self.kpi_visitors.set_value(str(len(visits)))
        self.lbl_today_visitors.setText(f"오늘 방문자: {len(visits)}")

        # 저장 용량
        total = 0
        for d in ["snapshots", "recordings"]:
            path = os.path.join(DATA_DIR, d)
            if os.path.exists(path):
                for f in os.listdir(path):
                    fp = os.path.join(path, f)
                    if os.path.isfile(fp):
                        total += os.path.getsize(fp)
        mb = total / (1024 * 1024)
        self.kpi_storage.set_value(f"{mb:.0f} MB" if mb < 1024 else f"{mb/1024:.1f} GB")

    # ═══════════════════════════════════════
    # 슬라이드 패널
    # ═══════════════════════════════════════

    def _toggle_top_panel(self):
        """상단 패널(헤더바 + KPI + 툴바) 슬라이드 토글"""
        if self._top_panel_expanded:
            # 접기: 헤더바 + 상단 패널 모두 숨김
            self.header.setVisible(False)
            self.top_panel.setVisible(False)
            self.btn_toggle_top.setText("▼")
        else:
            # 펼치기: 헤더바 + 상단 패널 모두 표시
            self.header.setVisible(True)
            self.top_panel.setVisible(True)
            self.btn_toggle_top.setText("▲")

        self._top_panel_expanded = not self._top_panel_expanded

    def _toggle_right_panel(self):
        anim = QPropertyAnimation(self.right_panel, b"maximumWidth", self)
        anim.setDuration(250)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        if self._panel_expanded:
            anim.setStartValue(self._panel_width)
            anim.setEndValue(0)
            self.btn_toggle_panel.setText("▶")
        else:
            self.right_panel.setVisible(True)
            anim.setStartValue(0)
            anim.setEndValue(self._panel_width)
            self.btn_toggle_panel.setText("◀")
        self._panel_expanded = not self._panel_expanded

        def on_finished():
            if not self._panel_expanded:
                self.right_panel.setVisible(False)
            else:
                self.right_panel.setFixedWidth(self._panel_width)
        anim.finished.connect(on_finished)
        anim.start()
        self._panel_anim = anim

    # ═══════════════════════════════════════
    # 탭 전환
    # ═══════════════════════════════════════

    def _on_tab_changed(self, index: int):
        self.stack.setCurrentIndex(index)

    # ═══════════════════════════════════════
    # 단축키
    # ═══════════════════════════════════════

    def _setup_shortcuts(self):
        sc = self.config.get("shortcuts", {})
        QShortcut(QKeySequence(sc.get("capture", "Ctrl+Shift+C")), self).activated.connect(self._capture_snapshot)
        QShortcut(QKeySequence(sc.get("record_toggle", "Ctrl+R")), self).activated.connect(self._toggle_recording)
        QShortcut(QKeySequence(sc.get("record_pause", "Ctrl+P")), self).activated.connect(self._toggle_pause)

    # ═══════════════════════════════════════
    # 상태바
    # ═══════════════════════════════════════

    def _setup_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("OfficeMonitor 시작됨")

    # ═══════════════════════════════════════
    # 시스템 트레이
    # ═══════════════════════════════════════

    def _setup_tray(self):
        icon_path = os.path.join(PROJECT_DIR, "icon.ico")
        if not os.path.exists(icon_path):
            return
        self._tray = QSystemTrayIcon(QIcon(icon_path), self)
        tray_menu = QMenu()
        tray_menu.addAction("열기", self._tray_show)
        tray_menu.addAction("종료", self.close)
        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _tray_show(self):
        self.showNormal()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._tray_show()

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized() and hasattr(self, "_tray"):
                self.hide()
                self._tray.showMessage("OfficeMonitor", "백그라운드에서 실행 중", QSystemTrayIcon.MessageIcon.Information, 2000)
        super().changeEvent(event)

    # ═══════════════════════════════════════
    # 종료
    # ═══════════════════════════════════════

    def closeEvent(self, event):
        if self._camera_thread:
            self._camera_thread.stop()
        if self._detection_thread:
            self._detection_thread.stop()
        if self._recording_thread:
            self._recording_thread.stop()
        if hasattr(self, "_tray"):
            self._tray.hide()
        event.accept()

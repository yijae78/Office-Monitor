"""OfficeMonitor 메인 윈도우 — 전체 통합"""

import os
import time
import cv2
import numpy as np
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStatusBar, QComboBox, QStackedWidget,
    QSizePolicy, QFileDialog, QSystemTrayIcon, QMenu, QApplication,
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

        # 녹화 목록 초기 로드
        self._refresh_rec_list()

        # 데이터 자동 정리 타이머
        cleanup_hours = self.config.get("storage", {}).get("cleanup_interval_hours", 1)
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.timeout.connect(self._run_cleanup)
        self._cleanup_timer.start(cleanup_hours * 3600 * 1000)
        QTimer.singleShot(10000, self._run_cleanup)  # 시작 10초 후 첫 실행

        # 불량 캡처 자동 정리 (60초마다)
        self._bad_face_timer = QTimer(self)
        self._bad_face_timer.timeout.connect(self._cleanup_bad_faces)
        self._bad_face_timer.start(60000)
        QTimer.singleShot(30000, self._cleanup_bad_faces)  # 시작 30초 후 첫 실행

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
        self.header.btn_refresh.clicked.connect(self._restart_app)
        self.header.btn_settings.clicked.connect(self._open_settings)
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
        self.btn_record.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.btn_record.clicked.connect(self._toggle_recording)

        self.btn_pause = QPushButton("⏸ 일시정지")
        self.btn_pause.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._toggle_pause)

        self.btn_capture = QPushButton("📷 캡처")
        self.btn_capture.setObjectName("btnCapture")
        self.btn_capture.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.btn_capture.clicked.connect(self._capture_snapshot)

        # 줌 버튼
        btn_zoom_out = QPushButton("－")
        btn_zoom_out.setFixedSize(30, 28)
        btn_zoom_out.setToolTip("축소")
        btn_zoom_out.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.06); color: #94a3b8;
                border: 1px solid rgba(255,255,255,0.10); border-radius: 6px;
                font-size: 16px; font-weight: bold; }
            QPushButton:hover { background: rgba(0,168,255,0.15); color: #38bdf8; }
        """)
        btn_zoom_out.clicked.connect(lambda: self.camera_widget.zoom_out())

        self._lbl_zoom = QLabel("1.0×")
        self._lbl_zoom.setFixedWidth(36)
        self._lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_zoom.setStyleSheet("font-size: 10px; color: #64748b;")

        btn_zoom_in = QPushButton("＋")
        btn_zoom_in.setFixedSize(30, 28)
        btn_zoom_in.setToolTip("확대")
        btn_zoom_in.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.06); color: #94a3b8;
                border: 1px solid rgba(255,255,255,0.10); border-radius: 6px;
                font-size: 16px; font-weight: bold; }
            QPushButton:hover { background: rgba(0,168,255,0.15); color: #38bdf8; }
        """)
        btn_zoom_in.clicked.connect(lambda: self.camera_widget.zoom_in())

        btn_zoom_reset = QPushButton("1:1")
        btn_zoom_reset.setFixedSize(32, 28)
        btn_zoom_reset.setToolTip("원본 크기")
        btn_zoom_reset.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.04); color: #64748b;
                border: 1px solid rgba(255,255,255,0.08); border-radius: 6px;
                font-size: 10px; }
            QPushButton:hover { background: rgba(255,255,255,0.08); color: #f1f5f9; }
        """)
        btn_zoom_reset.clicked.connect(lambda: self.camera_widget.zoom_reset())

        tb_layout.addWidget(cam_label)
        tb_layout.addWidget(self.combo_camera)
        tb_layout.addSpacing(12)
        tb_layout.addWidget(self.btn_record)
        tb_layout.addWidget(self.btn_pause)
        tb_layout.addSpacing(12)
        tb_layout.addWidget(self.btn_capture)
        tb_layout.addStretch()
        tb_layout.addWidget(btn_zoom_out)
        tb_layout.addWidget(self._lbl_zoom)
        tb_layout.addWidget(btn_zoom_in)
        tb_layout.addWidget(btn_zoom_reset)
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

        self.btn_toggle_panel = QPushButton("▶")
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
        from PyQt6.QtWidgets import QScrollArea

        panel = QWidget()
        panel.setMinimumWidth(0)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        # 스크롤 영역으로 감싸기
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
        """)
        scroll.viewport().setStyleSheet("background: transparent;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(8)

        # 카메라 정보
        cam_card, cam_lay = self._create_collapsible_card("카메라 정보")
        self.lbl_cam_status = QLabel("연결 대기 중...")
        self.lbl_cam_status.setObjectName("statusError")
        self.lbl_cam_status.setWordWrap(True)
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

        # 녹화 상태 + 목록
        rec_card, rec_lay = self._create_collapsible_card("녹화")
        self.lbl_rec_status = QLabel("대기 중")
        self.lbl_rec_status.setObjectName("subtitleLabel")
        rec_lay.addWidget(self.lbl_rec_status)
        self.lbl_rec_time = QLabel("녹화 시간: 00:00:00")
        self.lbl_rec_time.setObjectName("subtitleLabel")
        rec_lay.addWidget(self.lbl_rec_time)

        # 저장 경로
        self.lbl_rec_dir = QLabel(f"저장: {os.path.join(DATA_DIR, 'recordings')}")
        self.lbl_rec_dir.setObjectName("subtitleLabel")
        self.lbl_rec_dir.setStyleSheet("font-size: 10px; color: #64748b;")
        self.lbl_rec_dir.setWordWrap(True)
        rec_lay.addWidget(self.lbl_rec_dir)

        # 녹화 목록 헤더 (토글 + 폴더 열기)
        rec_header_row = QHBoxLayout()
        rec_header_row.setContentsMargins(0, 4, 0, 0)

        self._btn_rec_list_toggle = QPushButton("  ▼  최근 녹화")
        self._btn_rec_list_toggle.setStyleSheet("""
            QPushButton { background: transparent; color: #94a3b8;
                border: none; font-size: 11px; font-weight: bold;
                text-align: left; padding: 2px 0; }
            QPushButton:hover { color: #f1f5f9; }
        """)
        self._btn_rec_list_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        rec_header_row.addWidget(self._btn_rec_list_toggle)
        rec_header_row.addStretch()

        btn_open_folder = QPushButton("📂 폴더")
        btn_open_folder.setFixedHeight(26)
        btn_open_folder.setToolTip("녹화 폴더 열기")
        btn_open_folder.setStyleSheet("""
            QPushButton { background: rgba(0,168,255,0.10); color: #38bdf8;
                border: 1px solid rgba(0,168,255,0.25); border-radius: 6px;
                font-size: 11px; padding: 2px 8px; }
            QPushButton:hover { background: rgba(0,168,255,0.20); color: #7dd3fc; }
        """)
        btn_open_folder.clicked.connect(lambda: os.startfile(os.path.join(DATA_DIR, "recordings")))
        rec_header_row.addWidget(btn_open_folder)
        rec_lay.addLayout(rec_header_row)

        self._rec_list_widget = QWidget()
        self._rec_list_layout = QVBoxLayout(self._rec_list_widget)
        self._rec_list_layout.setContentsMargins(0, 0, 0, 0)
        self._rec_list_layout.setSpacing(4)
        rec_lay.addWidget(self._rec_list_widget)

        def toggle_rec_list():
            vis = not self._rec_list_widget.isVisible()
            self._rec_list_widget.setVisible(vis)
            self._btn_rec_list_toggle.setText(
                "  ▼  최근 녹화" if vis else "  ▶  최근 녹화"
            )
        self._btn_rec_list_toggle.clicked.connect(toggle_rec_list)

        layout.addWidget(rec_card)

        # 방문자 타임라인
        self.timeline = VisitorTimeline()
        layout.addWidget(self.timeline, 1)

        scroll.setWidget(scroll_content)
        panel_layout.addWidget(scroll)

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
        self._detection_thread.face_captured.connect(self._on_face_captured)
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
        # 줌 레이블 갱신
        if hasattr(self, '_lbl_zoom'):
            self._lbl_zoom.setText(f"{self.camera_widget._zoom:.1f}×")

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
            saved_path = self._recording_thread._current_path
            self._recording_thread.stop_recording()
            self.btn_record.setText("● 녹화")
            self.btn_record.setProperty("recording", "false")
            self.btn_pause.setEnabled(False)
            if saved_path:
                ToastWidget.show_toast(self, f"녹화 저장: {os.path.basename(saved_path)}", True)
                self.status_bar.showMessage(f"녹화 파일 저장됨: {saved_path}")
            self._refresh_rec_list()
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
    # 얼굴 자동 캡처 알림
    # ═══════════════════════════════════════

    def _on_face_captured(self, pending_id: int):
        """미등록 얼굴 자동 캡처 → 토스트 알림"""
        ToastWidget.show_toast(self, "새 얼굴이 캡처되었습니다 — 방문자관리에서 확인", False)
        self.status_bar.showMessage(f"미등록 얼굴 자동 캡처 (ID: {pending_id})")
        # 방문자관리 탭이 열려있으면 즉시 갱신
        if hasattr(self, '_visitor_view'):
            self._visitor_view.refresh()

    # ═══════════════════════════════════════
    # 카메라 상태
    # ═══════════════════════════════════════

    def _refresh_rec_list(self):
        """녹화 목록 갱신 (최근 10개)"""
        # 기존 아이템 제거
        while self._rec_list_layout.count():
            item = self._rec_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        recs = database.execute(
            "SELECT * FROM recordings ORDER BY start_time DESC LIMIT 10", fetch="all")

        if not recs:
            empty = QLabel("녹화 없음")
            empty.setStyleSheet("font-size: 11px; color: #64748b;")
            self._rec_list_layout.addWidget(empty)
            return

        for rec in recs:
            file_path = rec["file_path"]

            item = QPushButton()
            item.setCursor(Qt.CursorShape.PointingHandCursor)
            item.clicked.connect(lambda checked, p=file_path: self._play_recording(p))

            # 시간 + 크기
            start = rec["start_time"] or ""
            size_mb = (rec["size_bytes"] or 0) / (1024 * 1024)
            item.setText(f"▶  {start[5:16]}  ({size_mb:.1f}MB)")
            item.setToolTip(f"클릭하여 재생: {os.path.basename(file_path)}")
            item.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.02); border-radius: 6px;
                    border: 1px solid rgba(255,255,255,0.05);
                    font-size: 10px; color: #94a3b8;
                    text-align: left; padding: 5px 8px;
                }
                QPushButton:hover {
                    background: rgba(34,197,94,0.08); color: #34d399;
                    border-color: rgba(34,197,94,0.2);
                }
            """)

            self._rec_list_layout.addWidget(item)

    def _play_recording(self, path: str):
        """녹화 파일 재생 (기본 프로그램으로 열기)"""
        if os.path.exists(path):
            os.startfile(path)
        else:
            self.status_bar.showMessage(f"파일을 찾을 수 없습니다: {path}")

    def _restart_app(self):
        """앱 내부 새로고침 — 엔진 재시작 + 데이터 리로드 (창 유지)"""
        try:
            self.status_bar.showMessage("새로고침 중...")
            QApplication.processEvents()

            # 1. 엔진 안전하게 중지
            if self._recording_thread and self._recording_thread.is_recording:
                self._recording_thread.stop_recording()
            if self._camera_thread:
                self._camera_thread.stop()
            if self._detection_thread:
                self._detection_thread.stop()
            if self._recording_thread:
                self._recording_thread.stop()

            self._camera_thread = None
            self._detection_thread = None
            self._recording_thread = None
            QApplication.processEvents()

            # 2. config 재로드
            import yaml
            config_path = os.path.join(PROJECT_DIR, "config.yaml")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f) or {}

            # 3. 엔진 재시작
            self._start_engines()

            # 4. 모든 UI 데이터 갱신
            self._update_kpi()
            self._refresh_rec_list()
            if hasattr(self, '_visitor_view'):
                self._visitor_view.refresh()
            if hasattr(self, '_stats_view'):
                self._stats_view._refresh()

            self.status_bar.showMessage("새로고침 완료", 3000)
            ToastWidget.show_toast(self, "새로고침 완료", True)
        except Exception as e:
            self.status_bar.showMessage(f"새로고침 오류: {e}")
            import traceback
            traceback.print_exc()

    def _open_settings(self):
        """설정 다이얼로그 열기"""
        from .settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.config, self)
        dialog.exec()
        if dialog.changed:
            ToastWidget.show_toast(self, "설정 저장됨 — 일부 항목은 재시작 후 적용", True)
            # 데모 데이터 변경 시 UI 갱신
            self._refresh_rec_list()
            self._update_kpi()
            if hasattr(self, '_visitor_view'):
                self._visitor_view.refresh()

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
    # 데이터 자동 정리
    # ═══════════════════════════════════════

    def _run_cleanup(self):
        """보존 기간 초과 데이터 자동 삭제"""
        days = self.config.get("storage", {}).get("retention_days", 3)
        try:
            # 오래된 방문 로그의 썸네일 파일 삭제
            old_logs = database.get_old_records("visit_logs", days)
            for log in (old_logs or []):
                thumb = log["thumbnail_path"] if "thumbnail_path" in log.keys() else None
                if thumb and os.path.exists(thumb):
                    os.remove(thumb)

            # DB 레코드 삭제
            database.delete_old_records("visit_logs", days)
            database.delete_old_records("snapshots", days)

            # 오래된 pending_faces (삭제 상태) 영구 제거
            deleted_faces = database.get_pending_faces("deleted") or []
            for f in deleted_faces:
                captured = f["captured_at"] or ""
                if captured and captured < (datetime.now() - __import__("datetime").timedelta(days=days)).strftime("%Y-%m-%d"):
                    if os.path.exists(f["image_path"]):
                        os.remove(f["image_path"])
                    database.hard_delete_pending_face(f["id"])

            # 오래된 녹화 파일 삭제
            old_recs = database.execute(
                "SELECT * FROM recordings WHERE start_time < datetime('now','localtime',?)",
                (f"-{days} days",), fetch="all")
            for rec in (old_recs or []):
                if os.path.exists(rec["file_path"]):
                    os.remove(rec["file_path"])
            database.execute(
                "DELETE FROM recordings WHERE start_time < datetime('now','localtime',?)",
                (f"-{days} days",))
        except Exception:
            pass

    def _cleanup_bad_faces(self):
        """불량 캡처 이미지 자동 삭제"""
        if self._detection_thread and self._detection_thread.isRunning():
            removed = self._detection_thread.cleanup_bad_pending_faces()
            if removed > 0:
                self.status_bar.showMessage(f"불량 캡처 {removed}개 자동 삭제됨")
                if hasattr(self, '_visitor_view'):
                    self._visitor_view.refresh()

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
            self.btn_toggle_panel.setText("◀")
        else:
            self.right_panel.setVisible(True)
            anim.setStartValue(0)
            anim.setEndValue(self._panel_width)
            self.btn_toggle_panel.setText("▶")
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
    # 반응형 레이아웃
    # ═══════════════════════════════════════

    def resizeEvent(self, event):
        """창 크기에 따라 오른쪽 패널 너비 동적 조절"""
        super().resizeEvent(event)
        w = self.width()
        # 창 너비의 22% (최소 200, 최대 360)
        new_width = max(200, min(360, int(w * 0.22)))
        if new_width != self._panel_width and self._panel_expanded:
            self._panel_width = new_width
            self.right_panel.setFixedWidth(new_width)

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

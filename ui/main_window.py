"""OfficeMonitor 메인 윈도우"""

import sys
import os
import yaml
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSplitter, QFrame, QStatusBar, QComboBox,
    QSizePolicy, QToolBar,
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon, QAction

from .camera_widget import CameraWidget
from .styles import MAIN_STYLE


class MainWindow(QMainWindow):
    """메인 윈도우"""

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self._camera_thread = None
        self._last_frame = None
        self._frame_count = 0
        self._fps_display = 0.0

        self.setWindowTitle("OfficeMonitor")
        self.setMinimumSize(900, 600)
        self.resize(1200, 750)
        self.setStyleSheet(MAIN_STYLE)

        self._setup_ui()
        self._setup_statusbar()
        self._start_camera()

        # FPS 갱신 타이머
        self._fps_timer = QTimer(self)
        self._fps_timer.timeout.connect(self._update_fps)
        self._fps_timer.start(1000)

    def _setup_ui(self):
        """UI 구성"""
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(8)

        # ── 상단 툴바 영역 ──
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(4, 4, 4, 4)
        toolbar_layout.setSpacing(12)

        # 카메라 선택
        cam_label = QLabel("카메라")
        cam_label.setObjectName("subtitleLabel")
        self.combo_camera = QComboBox()
        self.combo_camera.addItem("Camera 0")
        self.combo_camera.addItem("Camera 1")
        self.combo_camera.currentIndexChanged.connect(self._on_camera_changed)

        # 녹화 버튼
        self.btn_record = QPushButton("● 녹화")
        self.btn_record.setObjectName("btnRecord")
        self.btn_record.setFixedWidth(100)
        self.btn_record.setEnabled(False)

        self.btn_pause = QPushButton("⏸ 일시정지")
        self.btn_pause.setFixedWidth(110)
        self.btn_pause.setEnabled(False)

        # 캡처 버튼
        self.btn_capture = QPushButton("📷 캡처")
        self.btn_capture.setObjectName("btnCapture")
        self.btn_capture.setFixedWidth(100)
        self.btn_capture.setEnabled(False)

        toolbar_layout.addWidget(cam_label)
        toolbar_layout.addWidget(self.combo_camera)
        toolbar_layout.addSpacing(20)
        toolbar_layout.addWidget(self.btn_record)
        toolbar_layout.addWidget(self.btn_pause)
        toolbar_layout.addSpacing(20)
        toolbar_layout.addWidget(self.btn_capture)
        toolbar_layout.addStretch()

        main_layout.addWidget(toolbar_widget)

        # ── 메인 콘텐츠 (스플리터) ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)

        # 좌측: 카메라 뷰어
        self.camera_widget = CameraWidget()
        splitter.addWidget(self.camera_widget)

        # 우측: 정보 패널
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)

        # 비율 7:3
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter, 1)

    def _create_right_panel(self) -> QWidget:
        """우측 정보 패널"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(12)

        # ── 카메라 정보 카드 ──
        cam_card = QFrame()
        cam_card.setObjectName("glassCard")
        cam_card_layout = QVBoxLayout(cam_card)
        cam_card_layout.setContentsMargins(16, 16, 16, 16)
        cam_card_layout.setSpacing(8)

        title = QLabel("카메라 정보")
        title.setObjectName("titleLabel")
        cam_card_layout.addWidget(title)

        self.lbl_cam_status = QLabel("연결 대기 중...")
        self.lbl_cam_status.setObjectName("statusError")
        cam_card_layout.addWidget(self.lbl_cam_status)

        self.lbl_cam_resolution = QLabel("해상도: -")
        self.lbl_cam_resolution.setObjectName("subtitleLabel")
        cam_card_layout.addWidget(self.lbl_cam_resolution)

        self.lbl_cam_fps = QLabel("FPS: -")
        self.lbl_cam_fps.setObjectName("subtitleLabel")
        cam_card_layout.addWidget(self.lbl_cam_fps)

        layout.addWidget(cam_card)

        # ── 감지 상태 카드 ──
        det_card = QFrame()
        det_card.setObjectName("glassCard")
        det_card_layout = QVBoxLayout(det_card)
        det_card_layout.setContentsMargins(16, 16, 16, 16)
        det_card_layout.setSpacing(8)

        title2 = QLabel("감지 상태")
        title2.setObjectName("titleLabel")
        det_card_layout.addWidget(title2)

        self.lbl_face_count = QLabel("감지된 얼굴: 0")
        self.lbl_face_count.setObjectName("subtitleLabel")
        det_card_layout.addWidget(self.lbl_face_count)

        self.lbl_today_visitors = QLabel("오늘 방문자: 0")
        self.lbl_today_visitors.setObjectName("subtitleLabel")
        det_card_layout.addWidget(self.lbl_today_visitors)

        layout.addWidget(det_card)

        # ── 녹화 상태 카드 ──
        rec_card = QFrame()
        rec_card.setObjectName("glassCard")
        rec_card_layout = QVBoxLayout(rec_card)
        rec_card_layout.setContentsMargins(16, 16, 16, 16)
        rec_card_layout.setSpacing(8)

        title3 = QLabel("녹화 상태")
        title3.setObjectName("titleLabel")
        rec_card_layout.addWidget(title3)

        self.lbl_rec_status = QLabel("대기 중")
        self.lbl_rec_status.setObjectName("subtitleLabel")
        rec_card_layout.addWidget(self.lbl_rec_status)

        self.lbl_rec_time = QLabel("녹화 시간: 00:00:00")
        self.lbl_rec_time.setObjectName("subtitleLabel")
        rec_card_layout.addWidget(self.lbl_rec_time)

        layout.addWidget(rec_card)

        layout.addStretch()
        return panel

    def _setup_statusbar(self):
        """상태바"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("OfficeMonitor 시작됨")

    def _start_camera(self):
        """카메라 스레드 시작"""
        from monitor_engine import CameraThread

        cam_cfg = self.config.get("camera", {})
        cam_id = cam_cfg.get("id", 0)
        resolution = cam_cfg.get("resolution", [1280, 720])
        fallback_ids = cam_cfg.get("fallback_ids", [])

        self._camera_thread = CameraThread(
            camera_id=cam_id,
            resolution=tuple(resolution),
            fallback_ids=fallback_ids,
        )
        self._camera_thread.frame_ready.connect(self._on_frame)
        self._camera_thread.camera_status.connect(self._on_camera_status)
        self._camera_thread.camera_info.connect(self._on_camera_info)
        self._camera_thread.start()

    def _on_frame(self, frame: np.ndarray, timestamp: float):
        """프레임 수신"""
        self._last_frame = frame
        self._frame_count += 1
        self.camera_widget.update_frame(frame)
        self.btn_capture.setEnabled(True)

    def _on_camera_status(self, message: str, is_ok: bool):
        """카메라 상태 변경"""
        self.lbl_cam_status.setText(message)
        self.lbl_cam_status.setObjectName("statusOK" if is_ok else "statusError")
        self.lbl_cam_status.setStyleSheet("")  # force style refresh
        self.lbl_cam_status.style().unpolish(self.lbl_cam_status)
        self.lbl_cam_status.style().polish(self.lbl_cam_status)

        if not is_ok:
            self.camera_widget.set_status(message, False)

        self.status_bar.showMessage(message)

    def _on_camera_info(self, info: dict):
        """카메라 정보 수신"""
        self.lbl_cam_resolution.setText(
            f"해상도: {info['width']}x{info['height']}"
        )
        self.combo_camera.setCurrentIndex(info.get("id", 0))

    def _on_camera_changed(self, index: int):
        """카메라 선택 변경"""
        if self._camera_thread and self._camera_thread.isRunning():
            self._camera_thread.stop()

        cam_cfg = self.config.get("camera", {})
        resolution = cam_cfg.get("resolution", [1280, 720])

        from monitor_engine import CameraThread
        self._camera_thread = CameraThread(
            camera_id=index,
            resolution=tuple(resolution),
        )
        self._camera_thread.frame_ready.connect(self._on_frame)
        self._camera_thread.camera_status.connect(self._on_camera_status)
        self._camera_thread.camera_info.connect(self._on_camera_info)
        self._camera_thread.start()

        self.camera_widget.set_status(f"Camera {index} 연결 중...", False)

    def _update_fps(self):
        """1초마다 FPS 갱신"""
        self._fps_display = self._frame_count
        self._frame_count = 0
        self.lbl_cam_fps.setText(f"FPS: {self._fps_display}")

    def closeEvent(self, event):
        """앱 종료 시 카메라 정리"""
        if self._camera_thread:
            self._camera_thread.stop()
        event.accept()

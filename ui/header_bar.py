"""상단 헤더바 — 앱 로고 + 세그먼트 컨트롤 + 설정 + 시계"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QButtonGroup, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from datetime import datetime


class HeaderBar(QWidget):
    """상단 헤더바"""

    tab_changed = pyqtSignal(int)  # 탭 인덱스 변경

    TAB_NAMES = ["모니터링", "방문자관리", "통계"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("headerBar")
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # ── 좌측: 로고 + 앱명 ──
        dot = QLabel("●")
        dot.setObjectName("appDot")
        dot.setFixedWidth(20)
        layout.addWidget(dot)

        title = QLabel("OfficeMonitor")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        layout.addSpacing(24)

        # ── 중앙: 세그먼트 컨트롤 ──
        segment_group = QWidget()
        segment_group.setObjectName("segmentGroup")
        seg_layout = QHBoxLayout(segment_group)
        seg_layout.setContentsMargins(3, 3, 3, 3)
        seg_layout.setSpacing(2)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        self._tab_buttons = []

        for i, name in enumerate(self.TAB_NAMES):
            btn = QPushButton(name)
            btn.setProperty("class", "segmentBtn")
            btn.setCheckable(True)
            btn.setProperty("active", "false")
            self._btn_group.addButton(btn, i)
            seg_layout.addWidget(btn)
            self._tab_buttons.append(btn)

        # 기본 활성 탭
        self._tab_buttons[0].setChecked(True)
        self._tab_buttons[0].setProperty("active", "true")
        self._tab_buttons[0].style().unpolish(self._tab_buttons[0])
        self._tab_buttons[0].style().polish(self._tab_buttons[0])

        self._btn_group.idClicked.connect(self._on_tab_clicked)
        layout.addWidget(segment_group)

        layout.addStretch()

        # ── 우측: 날짜 + 설정 + 시계 ──
        self.date_label = QLabel()
        self.date_label.setObjectName("dateLabel")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.date_label)

        layout.addSpacing(8)

        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setObjectName("settingsBtn")
        self.btn_settings.setFixedSize(36, 36)
        layout.addWidget(self.btn_settings)

        self.clock_label = QLabel()
        self.clock_label.setObjectName("clockLabel")
        self.clock_label.setFixedWidth(70)
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.clock_label)

        # 시계 타이머
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

    def _on_tab_clicked(self, tab_id: int):
        """세그먼트 버튼 클릭 처리"""
        for i, btn in enumerate(self._tab_buttons):
            btn.setProperty("active", "true" if i == tab_id else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.tab_changed.emit(tab_id)

    def _update_clock(self):
        now = datetime.now()
        self.clock_label.setText(now.strftime("%H:%M:%S"))
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        wd = weekdays[now.weekday()]
        self.date_label.setText(f"{now.strftime('%Y.%m.%d')} ({wd})")

    def set_active_tab(self, index: int):
        """외부에서 탭 변경"""
        if 0 <= index < len(self._tab_buttons):
            self._tab_buttons[index].setChecked(True)
            self._on_tab_clicked(index)

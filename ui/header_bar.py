"""상단 헤더바 — 앱 로고 + 세그먼트 컨트롤 + 설정 + 시계 (반응형)"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QButtonGroup, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from datetime import datetime


class HeaderBar(QWidget):
    """상단 헤더바 — 창 크기에 따라 요소 축소/숨김"""

    tab_changed = pyqtSignal(int)  # 탭 인덱스 변경

    TAB_NAMES = ["모니터링", "방문자관리", "통계"]
    TAB_SHORT = ["모니터", "방문자", "통계"]  # 좁은 창용 축약명

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("headerBar")
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        # ── 좌측: 로고 + 앱명 ──
        self._dot = QLabel("●")
        self._dot.setObjectName("appDot")
        self._dot.setFixedWidth(20)
        layout.addWidget(self._dot)

        self._title = QLabel("OfficeMonitor")
        self._title.setObjectName("appTitle")
        self._title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._title)

        layout.addSpacing(12)

        # ── 중앙: 세그먼트 컨트롤 ──
        self._segment_group = QWidget()
        self._segment_group.setObjectName("segmentGroup")
        self._segment_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        seg_layout = QHBoxLayout(self._segment_group)
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
            btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            self._btn_group.addButton(btn, i)
            seg_layout.addWidget(btn)
            self._tab_buttons.append(btn)

        # 기본 활성 탭
        self._tab_buttons[0].setChecked(True)
        self._tab_buttons[0].setProperty("active", "true")
        self._tab_buttons[0].style().unpolish(self._tab_buttons[0])
        self._tab_buttons[0].style().polish(self._tab_buttons[0])

        self._btn_group.idClicked.connect(self._on_tab_clicked)
        layout.addWidget(self._segment_group)

        layout.addStretch()

        # ── 우측: 날짜시간 → 새로고침 → 설정 (제일 끝) ──
        self.datetime_label = QLabel()
        self.datetime_label.setObjectName("clockLabel")
        self.datetime_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.datetime_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.datetime_label)

        layout.addSpacing(8)

        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setObjectName("settingsBtn")
        self.btn_refresh.setFixedSize(36, 36)
        self.btn_refresh.setToolTip("앱 새로고침")
        layout.addWidget(self.btn_refresh)

        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setObjectName("settingsBtn")
        self.btn_settings.setFixedSize(36, 36)
        self.btn_settings.setToolTip("설정")
        layout.addWidget(self.btn_settings)

        # 현재 반응형 상태 추적
        self._compact_mode = False

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
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        wd = weekdays[now.weekday()]
        if self._compact_mode:
            self.datetime_label.setText(now.strftime("%H:%M"))
        else:
            self.datetime_label.setText(
                f"{now.strftime('%Y.%m.%d')} ({wd})  {now.strftime('%H:%M:%S')}"
            )

    def resizeEvent(self, event):
        """창 크기에 따라 헤더 요소 축소/숨김"""
        super().resizeEvent(event)
        w = self.width()

        # 600px 미만: 컴팩트 모드 — 탭 이름 축약, 앱명 숨김, 시간만 표시
        compact = w < 600
        if compact != self._compact_mode:
            self._compact_mode = compact
            names = self.TAB_SHORT if compact else self.TAB_NAMES
            for i, btn in enumerate(self._tab_buttons):
                btn.setText(names[i])
            self._title.setVisible(not compact)
            self._update_clock()

    def set_active_tab(self, index: int):
        """외부에서 탭 변경"""
        if 0 <= index < len(self._tab_buttons):
            self._tab_buttons[index].setChecked(True)
            self._on_tab_clicked(index)

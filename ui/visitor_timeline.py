"""오늘 방문자 타임라인 위젯"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QSizePolicy,
    QPushButton,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor

from .design_tokens import Q_GREEN, Q_AMBER, Q_TEXT_SECONDARY, SPACE_2, SPACE_3


class VisitorTimelineItem(QWidget):
    """타임라인 개별 항목"""

    def __init__(self, time_str: str, name: str, thumbnail: QPixmap = None,
                 is_registered: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("timelineItem")
        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # 시간
        time_label = QLabel(time_str)
        time_label.setObjectName("subtitleLabel")
        time_label.setFixedWidth(44)
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(time_label)

        # 아바타 (원형, 이름 이니셜)
        avatar = AvatarLabel(36, thumbnail, Q_GREEN if is_registered else Q_AMBER, initial=name[:1] if name else "?")
        layout.addWidget(avatar)

        # 이름
        name_label = QLabel(name)
        name_label.setStyleSheet(
            f"color: {'#f1f5f9' if is_registered else '#fbbf24'}; font-size: 13px; font-weight: bold;"
        )
        layout.addWidget(name_label, 1)


class AvatarLabel(QWidget):
    """원형 아바타"""

    def __init__(self, size: int = 36, pixmap: QPixmap = None,
                 border_color: QColor = Q_GREEN, initial: str = "?", parent=None):
        super().__init__(parent)
        self._size = size
        self._pixmap = pixmap
        self._border_color = border_color
        self._initial = initial
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 보더
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._border_color)
        painter.drawEllipse(0, 0, self._size, self._size)

        # 내부
        if self._pixmap and not self._pixmap.isNull():
            path = QPainterPath()
            path.addEllipse(2, 2, self._size - 4, self._size - 4)
            painter.setClipPath(path)
            scaled = self._pixmap.scaled(
                self._size - 4, self._size - 4,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(2, 2, scaled)
        else:
            # 이니셜 표시
            painter.setBrush(QColor(30, 40, 60))
            painter.drawEllipse(2, 2, self._size - 4, self._size - 4)
            painter.setPen(QColor(200, 210, 220))
            from PyQt6.QtGui import QFont
            font = QFont("Pretendard Variable", 12)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._initial)

        painter.end()


class VisitorTimeline(QWidget):
    """오늘 방문자 타임라인 (스크롤 가능, 글래스 카드)"""

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 글래스 카드 프레임
        from PyQt6.QtWidgets import QFrame
        self._card = QFrame()
        self._card.setObjectName("glassCard")
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # 토글 헤더 (cardHeader 스타일로 통일)
        self._toggle_btn = QPushButton("  ▼  오늘 방문자")
        self._toggle_btn.setObjectName("cardHeader")
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle)
        card_layout.addWidget(self._toggle_btn)

        # 스크롤 영역
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                width: 8px; background: rgba(255,255,255,0.06);
                border-radius: 4px; margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.25);
                border-radius: 3px; min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0,168,255,0.45);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0; background: transparent;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(8, 0, 8, 8)
        self._container_layout.setSpacing(2)
        self._container_layout.addStretch()

        self._scroll.setWidget(self._container)
        self._collapsed = False
        card_layout.addWidget(self._scroll, 1)

        # 펼침: stretch로 공간 채움 / 접힘: 헤더만 남도록
        self._card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        outer.addWidget(self._card, 1)

        # 빈 상태
        self._empty_label = QLabel("방문자가 없습니다")
        self._empty_label.setObjectName("emptyStateDesc")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._container_layout.insertWidget(0, self._empty_label)

    def _toggle(self):
        self._collapsed = not self._collapsed
        self._scroll.setVisible(not self._collapsed)
        if self._collapsed:
            # 접힘: 헤더 높이만 차지
            h = self._toggle_btn.sizeHint().height() + 2
            self._card.setFixedHeight(h)
            self._card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            self.setFixedHeight(h)
        else:
            # 펼침: 남은 공간 채움
            self._card.setMaximumHeight(16777215)
            self._card.setMinimumHeight(0)
            self._card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            self.setMaximumHeight(16777215)
            self.setMinimumHeight(0)
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._update_title()

    def _update_title(self):
        # 방문자 수 카운트 (stretch, empty_label 제외)
        count = 0
        for i in range(self._container_layout.count()):
            item = self._container_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), VisitorTimelineItem):
                count += 1
        arrow = "▶" if self._collapsed else "▼"
        suffix = f" ({count})" if count > 0 else ""
        self._toggle_btn.setText(f"  {arrow}  오늘 방문자{suffix}")

    def add_visitor(self, time_str: str, name: str, thumbnail: QPixmap = None,
                    is_registered: bool = True):
        """방문자 추가 (최신이 위에)"""
        self._empty_label.hide()
        item = VisitorTimelineItem(time_str, name, thumbnail, is_registered)
        self._container_layout.insertWidget(
            self._container_layout.count() - 1, item
        )
        self._update_title()

    def clear(self):
        """타임라인 초기화"""
        while self._container_layout.count() > 1:  # stretch 유지
            item = self._container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._empty_label.show()
        self._update_title()

    def add_demo_data(self):
        """데모 데이터 추가"""
        demos = [
            ("15:32", "김철수", True),
            ("14:15", "미등록 방문자", False),
            ("13:02", "박영희", True),
            ("11:45", "이민수", True),
            ("10:30", "미등록 방문자", False),
            ("09:15", "최지영", True),
        ]
        for time_str, name, reg in demos:
            self.add_visitor(time_str, name, is_registered=reg)

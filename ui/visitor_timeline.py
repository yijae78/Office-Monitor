"""오늘 방문자 타임라인 위젯"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QSizePolicy,
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

        # 아바타 (원형)
        avatar = AvatarLabel(36, thumbnail, Q_GREEN if is_registered else Q_AMBER)
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
                 border_color: QColor = Q_GREEN, parent=None):
        super().__init__(parent)
        self._size = size
        self._pixmap = pixmap
        self._border_color = border_color
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self._size / 2
        radius = center - 1.5

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
            # 기본 아바타 (이니셜 원)
            painter.setBrush(QColor(30, 40, 60))
            painter.drawEllipse(2, 2, self._size - 4, self._size - 4)
            painter.setPen(QColor(148, 163, 184))
            from PyQt6.QtGui import QFont
            font = QFont("Pretendard Variable", 12)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "?")

        painter.end()


class VisitorTimeline(QWidget):
    """오늘 방문자 타임라인 (스크롤 가능)"""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 제목
        title = QLabel("오늘 방문자")
        title.setObjectName("titleLabel")
        title.setContentsMargins(4, 0, 0, 4)
        layout.addWidget(title)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(2)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        layout.addWidget(scroll, 1)

        # 빈 상태
        self._empty_label = QLabel("방문자가 없습니다")
        self._empty_label.setObjectName("emptyStateDesc")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._container_layout.insertWidget(0, self._empty_label)

    def add_visitor(self, time_str: str, name: str, thumbnail: QPixmap = None,
                    is_registered: bool = True):
        """방문자 추가 (최신이 위에)"""
        self._empty_label.hide()
        item = VisitorTimelineItem(time_str, name, thumbnail, is_registered)
        # stretch 앞에 삽입
        self._container_layout.insertWidget(
            self._container_layout.count() - 1, item
        )

    def clear(self):
        """타임라인 초기화"""
        while self._container_layout.count() > 1:  # stretch 유지
            item = self._container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._empty_label.show()

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

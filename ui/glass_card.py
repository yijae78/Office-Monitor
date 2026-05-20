"""글래스모피즘 카드 베이스 클래스"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor
from .design_tokens import (
    Q_BG_RAISED, Q_BORDER, RADIUS_LG, SPACE_4, SPACE_2,
    Q_CYAN, Q_GREEN, Q_BLUE, Q_AMBER, Q_RED, Q_TEXT_PRIMARY,
    font_title,
)


class GlassCard(QFrame):
    """글래스모피즘 카드 — 그림자 + 호버 + 상단 컬러바 지원"""

    def __init__(self, title: str = "", accent_color: QColor = None, parent=None):
        super().__init__(parent)
        self.setObjectName("glassCard")
        self._accent_color = accent_color

        # 그림자
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(16)
        self._shadow.setOffset(0, 4)
        self._shadow.setColor(QColor(0, 0, 0, 76))
        self.setGraphicsEffect(self._shadow)

        # 레이아웃
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        self._layout.setSpacing(SPACE_2)

        # 제목
        if title:
            self._title_label = QLabel(title)
            self._title_label.setObjectName("titleLabel")
            self._layout.addWidget(self._title_label)

        # 상단 컬러바 스타일
        if accent_color:
            r, g, b, _ = accent_color.getRgb()
            self.setStyleSheet(f"""
                QFrame#glassCard {{
                    border-top: 3px solid rgb({r},{g},{b});
                }}
            """)

    @property
    def card_layout(self) -> QVBoxLayout:
        return self._layout

    def add_widget(self, widget):
        self._layout.addWidget(widget)

    def add_stretch(self):
        self._layout.addStretch()

    def enterEvent(self, event):
        """호버 시 그림자 강화"""
        anim = QPropertyAnimation(self._shadow, b"blurRadius", self)
        anim.setDuration(150)
        anim.setStartValue(self._shadow.blurRadius())
        anim.setEndValue(32)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """호버 해제 시 그림자 복원"""
        anim = QPropertyAnimation(self._shadow, b"blurRadius", self)
        anim.setDuration(250)
        anim.setStartValue(self._shadow.blurRadius())
        anim.setEndValue(16)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        super().leaveEvent(event)

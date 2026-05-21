"""KPI 카드 위젯 — QPainter 기반, 글로우 펄스 애니메이션"""

from PyQt6.QtWidgets import QWidget, QGraphicsDropShadowEffect, QSizePolicy
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, pyqtProperty, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QLinearGradient, QPen

from .design_tokens import (
    Q_BG_RAISED, Q_TEXT_PRIMARY, Q_TEXT_SECONDARY, Q_BORDER, Q_CYAN,
    RADIUS_LG, FONT_UI,
)


class KPICard(QWidget):
    """KPI 수치 카드 — 숫자를 크게 표시, 하단 컬러바, 글로우 펄스"""

    def __init__(self, label: str = "", value: str = "0", accent: QColor = Q_CYAN, parent=None):
        super().__init__(parent)
        self._label = label.upper()
        self._value = value
        self._accent = accent
        self._glow_opacity = 0.15

        self.setMinimumHeight(70)
        self.setMaximumHeight(100)
        self.setMinimumWidth(80)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        # 그림자
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 76))
        self.setGraphicsEffect(shadow)

        # 글로우 펄스 애니메이션
        self._glow_anim = QPropertyAnimation(self, b"glowOpacity", self)
        self._glow_anim.setDuration(2500)
        self._glow_anim.setStartValue(0.15)
        self._glow_anim.setEndValue(0.35)
        self._glow_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._glow_anim.setLoopCount(-1)  # 무한 반복
        # 왕복
        self._glow_anim.finished.connect(lambda: None)
        QTimer.singleShot(100, self._start_glow)

    def _start_glow(self):
        self._glow_anim.setDirection(QPropertyAnimation.Direction.Forward)
        self._glow_anim.start()
        # 왕복 타이머
        self._reverse_timer = QTimer(self)
        self._reverse_timer.timeout.connect(self._toggle_glow_direction)
        self._reverse_timer.start(2500)

    def _toggle_glow_direction(self):
        if self._glow_anim.direction() == QPropertyAnimation.Direction.Forward:
            self._glow_anim.setDirection(QPropertyAnimation.Direction.Backward)
        else:
            self._glow_anim.setDirection(QPropertyAnimation.Direction.Forward)

    @pyqtProperty(float)
    def glowOpacity(self):
        return self._glow_opacity

    @glowOpacity.setter
    def glowOpacity(self, val):
        self._glow_opacity = val
        self.update()

    def set_value(self, value: str):
        self._value = value
        self.update()

    def set_label(self, label: str):
        self._label = label.upper()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect())

        # 배경 — 깊은 바다색 그라디언트
        bg_grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        bg_grad.setColorAt(0.0, QColor(8, 27, 52, 220))     # 심해 네이비
        bg_grad.setColorAt(0.5, QColor(10, 36, 65, 200))     # 미드나잇 블루
        bg_grad.setColorAt(1.0, QColor(6, 22, 42, 230))      # 딥 오션
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_grad)
        painter.drawRoundedRect(rect, RADIUS_LG, RADIUS_LG)

        # 보더
        painter.setPen(QPen(Q_BORDER, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), RADIUS_LG, RADIUS_LG)

        # 하단 컬러바
        bar_rect = QRectF(rect.left() + 1, rect.bottom() - 4, rect.width() - 2, 3)
        accent_with_alpha = QColor(self._accent)
        accent_with_alpha.setAlphaF(0.6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent_with_alpha)
        painter.drawRoundedRect(bar_rect, 2, 2)

        # 글로우 (하단)
        glow_color = QColor(self._accent)
        glow_color.setAlphaF(self._glow_opacity)
        glow_grad = QLinearGradient(rect.left(), rect.bottom() - 20, rect.left(), rect.bottom())
        glow_grad.setColorAt(0, QColor(0, 0, 0, 0))
        glow_grad.setColorAt(1, glow_color)
        painter.setBrush(glow_grad)
        painter.drawRoundedRect(
            QRectF(rect.left(), rect.bottom() - 20, rect.width(), 20),
            0, 0,
        )

        # 반응형 폰트/위치 계산
        h = rect.height()
        pad = max(8, min(16, rect.width() * 0.08))
        val_size = max(16, min(28, int(h * 0.35)))
        lbl_size = max(8, min(10, int(h * 0.12)))
        val_h = h * 0.5
        lbl_y = rect.top() + h * 0.6

        # 수치
        font_val = QFont(FONT_UI, val_size)
        font_val.setWeight(QFont.Weight.Bold)
        painter.setFont(font_val)
        painter.setPen(Q_TEXT_PRIMARY)
        painter.drawText(
            QRectF(rect.left() + pad, rect.top() + 8, rect.width() - pad * 2, val_h),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._value,
        )

        # 라벨
        font_lbl = QFont(FONT_UI, lbl_size)
        font_lbl.setWeight(QFont.Weight.DemiBold)
        font_lbl.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        painter.setFont(font_lbl)
        painter.setPen(Q_TEXT_SECONDARY)
        painter.drawText(
            QRectF(rect.left() + pad, lbl_y, rect.width() - pad * 2, 20),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._label,
        )

        painter.end()

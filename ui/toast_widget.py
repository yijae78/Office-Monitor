"""토스트 알림 위젯 — 화면 우하단 자동 사라짐"""

from PyQt6.QtWidgets import QLabel, QWidget, QHBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont


class ToastWidget(QLabel):
    """토스트 알림 — 2.5초 후 페이드아웃"""

    _active_toasts = []

    def __init__(self, parent, message: str, is_ok: bool = True):
        super().__init__(parent)
        color = "#22c55e" if is_ok else "#f59e0b"
        border_color = "rgba(34,197,94,0.4)" if is_ok else "rgba(245,158,11,0.4)"

        self.setText(f"  {'●' if is_ok else '▲'}  {message}")
        self.setStyleSheet(f"""
            background: rgba(17,24,39,0.95);
            color: {color};
            border: 1px solid {border_color};
            border-left: 3px solid {color};
            border-radius: 10px;
            padding: 10px 16px;
            font-size: 13px;
            font-weight: bold;
        """)
        self.setFont(QFont("Pretendard Variable", 12))
        self.adjustSize()
        self.setFixedHeight(40)
        self.setMinimumWidth(200)

        # 위치: 우하단
        offset = len(ToastWidget._active_toasts) * 50
        px = parent.width() - self.width() - 24
        py = parent.height() - 80 - offset
        self.move(px, py)
        self.show()
        self.raise_()

        ToastWidget._active_toasts.append(self)

        # 2.5초 후 페이드아웃
        QTimer.singleShot(2500, self._fade_out)

    def _fade_out(self):
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        anim = QPropertyAnimation(self._opacity, b"opacity", self)
        anim.setDuration(400)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(self._remove)
        anim.start()
        self._anim = anim

    def _remove(self):
        if self in ToastWidget._active_toasts:
            ToastWidget._active_toasts.remove(self)
        self.deleteLater()

    @staticmethod
    def show_toast(parent, message: str, is_ok: bool = True):
        ToastWidget(parent, message, is_ok)
